#!/usr/bin/env python3
"""Generate deterministic model_03_target_state_vector rows from feature rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

from model_runtime.config import database_url_file

from models.model_03_target_state_vector import generator

DEFAULT_DB_URL_FILE = database_url_file()
DEFAULT_FEATURE_TABLE = "m03_target_state_vector_feature_generation"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
PRIMARY_JSON_COLUMNS: set[str] = set()
EXPLAINABILITY_JSON_COLUMNS = {"target_context_state", "target_state_embedding", "explanation_payload_json"}
DIAGNOSTICS_JSON_COLUMNS = {"diagnostic_payload_json"}
RETIRED_STATE_WINDOWS = ("5min", "15min", "60min", "390min")
RETIRED_WINDOWED_SCORE_NAMES = (
    "target_direction_score",
    "target_direction_strength_score",
    "target_trend_quality_score",
    "target_path_stability_score",
    "target_noise_score",
    "target_transition_risk_score",
    "target_state_persistence_score",
    "target_exhaustion_risk_score",
    "context_direction_alignment_score",
    "context_support_quality_score",
    "tradability_score",
)
RETIRED_PRIMARY_COLUMNS = (
    "target_context_state",
    "target_state_embedding",
    "state_cluster_id",
    "state_quality_diagnostics",
    *(
        f"3_{score_name}_{window}"
        for window in RETIRED_STATE_WINDOWS
        for score_name in RETIRED_WINDOWED_SCORE_NAMES
    ),
)
PRIMARY_KEY = ("target_candidate_id", "available_time", "model_version")
SUPPORT_PRIMARY_KEY = ("target_candidate_id", "available_time", "model_version")
INSERT_BATCH_SIZE = 1000
MODEL_WRITE_BATCH_SIZE = 1000


def _read_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("feature_rows") or payload.get("model_rows") or []
    return [dict(row) for row in payload]


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), encoding="utf-8")


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for SQL generation; install psycopg[binary].") from error
    return psycopg, dict_row


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _quote_column_identifier(identifier: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL column identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _column_type(column: str) -> str:
    if column in PRIMARY_JSON_COLUMNS or column in EXPLAINABILITY_JSON_COLUMNS or column in DIAGNOSTICS_JSON_COLUMNS:
        return "JSONB"
    if column in {"available_time", "tradeable_time"}:
        return "TIMESTAMPTZ"
    if column in {"3_evidence_count", "present_score_output_count", "missing_score_output_count"}:
        return "INTEGER"
    if column.startswith("3_"):
        return "DOUBLE PRECISION"
    return "TEXT"


def _feature_rows_query(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None = None,
) -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('f."available_time" >= %s')
        params.append(source_start)
    if source_end:
        where.append('f."available_time" < %s')
        params.append(source_end)
    if target_symbol:
        where.append('UPPER(s."symbol") = %s')
        params.append(target_symbol.upper())
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    sql = f"""
        SELECT
          f.*,
          COALESCE(
            f."market_context_state_ref",
            l2."market_context_state_ref",
            'model_01_market_regime:' || replace(l1."available_time"::text, ' ', 'T')
          ) AS "market_context_state_ref",
          COALESCE(
            f."sector_context_state_ref",
            'model_02_sector_context:' || replace(l2."available_time"::text, ' ', 'T') || ':' || l2."sector_or_industry_symbol"
          ) AS "sector_context_state_ref"
        FROM {_qualified(source_schema, source_table)} AS f
        LEFT JOIN {_qualified("trading_data", "m03_target_state_vector_data_acquisition")} AS s
          ON s."target_candidate_id" = f."target_candidate_id"
         AND s."available_time" = f."available_time"
        LEFT JOIN LATERAL (
          SELECT *
          FROM {_qualified("trading_model", "m02_sector_context_model_generation")} AS candidate_l2
          WHERE candidate_l2."sector_or_industry_symbol" = s."symbol"
            AND candidate_l2."available_time" <= f."available_time"
          ORDER BY candidate_l2."available_time" DESC
          LIMIT 1
        ) AS l2 ON TRUE
        LEFT JOIN LATERAL (
          SELECT *
          FROM {_qualified("trading_model", "m01_market_regime_model_generation")} AS candidate_l1
          WHERE candidate_l1."available_time" <= f."available_time"
          ORDER BY candidate_l1."available_time" DESC
          LIMIT 1
        ) AS l1 ON TRUE
        {where_sql}
        ORDER BY f."available_time" ASC, f."target_candidate_id" ASC
        """
    return sql, params


def fetch_feature_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None = None,
) -> list[dict[str, Any]]:
    query, params = _feature_rows_query(
        cursor,
        source_schema=source_schema,
        source_table=source_table,
        source_start=source_start,
        source_end=source_end,
        target_symbol=target_symbol,
    )
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def stream_feature_rows(
    conn: Any,
    *,
    cursor_name: str,
    dict_row: Any,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None = None,
) -> Iterable[dict[str, Any]]:
    with conn.cursor() as metadata_cursor:
        query, params = _feature_rows_query(
            metadata_cursor,
            source_schema=source_schema,
            source_table=source_table,
            source_start=source_start,
            source_end=source_end,
            target_symbol=target_symbol,
        )
    with conn.cursor(name=cursor_name, row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        for row in cursor:
            yield dict(row)


def _ensure_table(cursor: Any, *, target_schema: str, target_table: str, columns: Sequence[str]) -> None:
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    column_defs = ",\n          ".join(f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns)
    pk_sql = ", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_qualified(target_schema, target_table)} (
          {column_defs},
          PRIMARY KEY ({pk_sql})
        )
        """
    )
    for column in columns:
        cursor.execute(f"ALTER TABLE {_qualified(target_schema, target_table)} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


def write_model_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    if not rows:
        return
    columns = list(generator.OUTPUT_COLUMNS)
    _ensure_table(cursor, target_schema=target_schema, target_table=target_table, columns=columns)
    qualified_table = _qualified(target_schema, target_table)
    for column in RETIRED_PRIMARY_COLUMNS:
        cursor.execute(f"ALTER TABLE {qualified_table} DROP COLUMN IF EXISTS {_quote_column_identifier(column)}")
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    placeholders = ["%s::jsonb" if column in PRIMARY_JSON_COLUMNS else "%s" for column in columns]
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in PRIMARY_KEY
    )
    conflict_sql = ", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)
    insert_sql = f"""
        INSERT INTO {_qualified(target_schema, target_table)} ({", ".join(quoted_columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}
    """
    batch: list[list[Any]] = []
    for row in rows:
        values = [json.dumps(row.get(column), sort_keys=True, default=str) if column in PRIMARY_JSON_COLUMNS else row.get(column) for column in columns]
        batch.append(values)
        if len(batch) >= INSERT_BATCH_SIZE:
            cursor.executemany(insert_sql, batch)
            batch.clear()
    if batch:
        cursor.executemany(insert_sql, batch)


def _write_support_rows_sql(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
    json_columns: set[str],
) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    _ensure_table(cursor, target_schema=target_schema, target_table=target_table, columns=columns)
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    placeholders = ["%s::jsonb" if column in json_columns else "%s" for column in columns]
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in SUPPORT_PRIMARY_KEY
    )
    conflict_sql = ", ".join(_quote_column_identifier(column) for column in SUPPORT_PRIMARY_KEY)
    insert_sql = f"""
        INSERT INTO {_qualified(target_schema, target_table)} ({", ".join(quoted_columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}
    """
    batch: list[list[Any]] = []
    for row in rows:
        values = [json.dumps(row.get(column), sort_keys=True, default=str) if column in json_columns else row.get(column) for column in columns]
        batch.append(values)
        if len(batch) >= INSERT_BATCH_SIZE:
            cursor.executemany(insert_sql, batch)
            batch.clear()
    if batch:
        cursor.executemany(insert_sql, batch)


def write_explainability_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    _write_support_rows_sql(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        json_columns=EXPLAINABILITY_JSON_COLUMNS,
    )


def write_diagnostics_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    _write_support_rows_sql(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        json_columns=DIAGNOSTICS_JSON_COLUMNS,
    )


def _write_model_batch(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    output_handle: TextIO | None,
    target_schema: str,
    target_table: str,
    explainability_table: str,
    diagnostics_table: str,
) -> None:
    if not rows:
        return
    write_model_rows_sql(cursor, generator.build_primary_rows(rows), target_schema=target_schema, target_table=target_table)
    write_explainability_rows_sql(
        cursor,
        generator.build_explainability_rows(rows),
        target_schema=target_schema,
        target_table=explainability_table,
    )
    write_diagnostics_rows_sql(
        cursor,
        generator.build_diagnostics_rows(rows),
        target_schema=target_schema,
        target_table=diagnostics_table,
    )
    if output_handle:
        output_handle.write("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows))


def generate_from_database(
    *,
    database_url: str,
    feature_schema: str,
    feature_table: str,
    target_schema: str,
    target_table: str,
    explainability_table: str,
    diagnostics_table: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None = None,
    model_version: str,
    output: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    output_tmp = None
    output_handle: TextIO | None = None
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output_tmp = output.with_name(f"{output.name}.tmp")
    try:
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            row_count = 0
            batch: list[dict[str, Any]] = []
            try:
                if output_tmp:
                    output_handle = output_tmp.open("w", encoding="utf-8")
                with conn.cursor() as write_cursor:
                    for feature_row in stream_feature_rows(
                        conn,
                        cursor_name="m03_target_state_vector_feature_stream",
                        dict_row=dict_row,
                        source_schema=feature_schema,
                        source_table=feature_table,
                        source_start=source_start,
                        source_end=source_end,
                        target_symbol=target_symbol,
                    ):
                        batch.append(generator.generate_ordered_row(feature_row, model_version=model_version))
                        if len(batch) >= MODEL_WRITE_BATCH_SIZE:
                            _write_model_batch(
                                write_cursor,
                                batch,
                                output_handle=output_handle,
                                target_schema=target_schema,
                                target_table=target_table,
                                explainability_table=explainability_table,
                                diagnostics_table=diagnostics_table,
                            )
                            row_count += len(batch)
                            batch.clear()
                    if batch:
                        _write_model_batch(
                            write_cursor,
                            batch,
                            output_handle=output_handle,
                            target_schema=target_schema,
                            target_table=target_table,
                            explainability_table=explainability_table,
                            diagnostics_table=diagnostics_table,
                        )
                        row_count += len(batch)
                        batch.clear()
            finally:
                if output_handle:
                    output_handle.close()
    except Exception:
        if output_tmp:
            output_tmp.unlink(missing_ok=True)
        raise
    if output_tmp and output:
        output_tmp.replace(output)
    return row_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path, help="JSON/JSONL m03_target_state_vector_feature_generation rows")
    parser.add_argument("--output", type=Path, help="Optional JSONL output path. Defaults to stdout for file mode.")
    parser.add_argument("--model-version", default=generator.MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true", help="Read feature rows from PostgreSQL and write model rows to PostgreSQL.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default="trading_data")
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_03_target_state_vector")
    parser.add_argument("--explainability-table", help="Optional explainability artifact table. Defaults to <target-table>_explainability.")
    parser.add_argument("--diagnostics-table", help="Optional diagnostics artifact table. Defaults to <target-table>_diagnostics.")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-symbol", help="Optional selected target symbol filter via m03_target_state_vector_data_acquisition.")
    args = parser.parse_args(argv)
    if args.from_database:
        row_count = generate_from_database(
            database_url=_database_url(args.database_url),
            feature_schema=args.feature_schema,
            feature_table=args.feature_table,
            target_schema=args.target_schema,
            target_table=args.target_table,
            explainability_table=args.explainability_table or f"{args.target_table}_explainability",
            diagnostics_table=args.diagnostics_table or f"{args.target_table}_diagnostics",
            source_start=args.source_start,
            source_end=args.source_end,
            target_symbol=args.target_symbol,
            model_version=args.model_version,
            output=args.output,
        )
        print(
            f"generated {row_count} rows into {args.target_schema}.{args.target_table} "
            f"with support artifacts {args.target_schema}.{args.explainability_table or args.target_table + '_explainability'} "
            f"and {args.target_schema}.{args.diagnostics_table or args.target_table + '_diagnostics'}"
        )
        return 0
    if not args.feature_rows:
        parser.error("--feature-rows is required unless --from-database is supplied")
    rows = generator.generate_rows(_read_rows(args.feature_rows), model_version=args.model_version)
    if args.output:
        _write_jsonl(args.output, rows)
    else:
        print("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

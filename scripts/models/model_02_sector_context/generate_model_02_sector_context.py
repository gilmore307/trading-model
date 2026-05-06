#!/usr/bin/env python3
"""Generate model_02_sector_context rows from Layer 2 feature SQL rows."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")

TEXT_COLUMNS = {
    "sector_or_industry_symbol",
    "model_id",
    "model_version",
    "market_context_state_ref",
    "2_sector_handoff_state",
    "2_sector_handoff_bias",
    "2_sector_handoff_reason_codes",
    "2_eligibility_state",
    "2_eligibility_reason_codes",
}
INTEGER_COLUMNS = {"2_sector_handoff_rank", "2_evidence_count"}


def _load_generator():
    return importlib.import_module("models.model_02_sector_context.generator")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for SQL generation; install psycopg[binary].") from error
    return psycopg, dict_row


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


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
    if column == "available_time":
        return "TIMESTAMPTZ"
    if column in TEXT_COLUMNS:
        return "TEXT"
    if column in INTEGER_COLUMNS:
        return "INTEGER"
    return "DOUBLE PRECISION"


def fetch_feature_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None = None,
    source_end: str | None = None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("snapshot_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("snapshot_time <= %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"SELECT * FROM {_qualified(source_schema, source_table)}{where_sql} ORDER BY snapshot_time ASC, candidate_symbol ASC, rotation_pair_id ASC",
        params,
    )
    rows: list[dict[str, Any]] = []
    for source_row in cursor.fetchall():
        row = dict(source_row)
        payload = row.pop("feature_payload_json", None)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, Mapping):
            row.update(payload)
        rows.append(row)
    return rows


def fetch_market_context_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None = None,
    source_end: str | None = None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("available_time <= %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(source_schema, source_table)}{where_sql} ORDER BY available_time ASC", params)
    return [dict(row) for row in cursor.fetchall()]


def _ensure_wide_table(cursor: Any, *, target_schema: str, target_table: str, columns: Sequence[str], primary_key: Sequence[str]) -> None:
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    column_defs = ",\n          ".join(f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns)
    pk_sql = ", ".join(_quote_column_identifier(column) for column in primary_key)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          {column_defs},
          PRIMARY KEY ({pk_sql})
        )
        """
    )
    for column in columns:
        cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


def _insert_wide_rows(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str, columns: Sequence[str], primary_key: Sequence[str]) -> None:
    if not rows:
        return
    _ensure_wide_table(cursor, target_schema=target_schema, target_table=target_table, columns=columns, primary_key=primary_key)
    qualified_table = _qualified(target_schema, target_table)
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in primary_key
    )
    conflict_sql = ", ".join(_quote_column_identifier(column) for column in primary_key)
    insert_sql = f"""
        INSERT INTO {qualified_table} ({", ".join(quoted_columns)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(insert_sql, [row.get(column) for column in columns])


def write_model_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    generator = _load_generator()
    _insert_wide_rows(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        columns=generator.OUTPUT_COLUMNS,
        primary_key=("available_time", "sector_or_industry_symbol"),
    )


def write_explainability_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    if not rows:
        return
    generator = _load_generator()
    columns = ["available_time", "sector_or_industry_symbol", *generator.EXPLAINABILITY_SCORE_COLUMNS, "explanation_payload_json"]
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    score_defs = ",\n          ".join(f"{_quote_column_identifier(column)} DOUBLE PRECISION" for column in generator.EXPLAINABILITY_SCORE_COLUMNS)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ NOT NULL,
          "sector_or_industry_symbol" TEXT NOT NULL,
          {score_defs},
          "explanation_payload_json" JSONB NOT NULL,
          PRIMARY KEY ("available_time", "sector_or_industry_symbol")
        )
        """
    )
    for column in generator.EXPLAINABILITY_SCORE_COLUMNS:
        cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} DOUBLE PRECISION")
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"explanation_payload_json\" JSONB NOT NULL DEFAULT '{{}}'::jsonb")
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in {"available_time", "sector_or_industry_symbol"}
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ({", ".join(quoted_columns)})
        VALUES ({", ".join(["%s"] * len(columns[:-1]))}, %s::jsonb)
        ON CONFLICT ("available_time", "sector_or_industry_symbol") DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(insert_sql, [*[row.get(column) for column in columns[:-1]], json.dumps(row.get("explanation_payload_json", {}), sort_keys=True, default=str)])


def write_diagnostics_rows_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    if not rows:
        return
    generator = _load_generator()
    columns = ["available_time", "sector_or_industry_symbol", *generator.DIAGNOSTIC_SCORE_COLUMNS, "diagnostic_payload_json"]
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    score_defs = ",\n          ".join(f"{_quote_column_identifier(column)} DOUBLE PRECISION" for column in generator.DIAGNOSTIC_SCORE_COLUMNS)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ NOT NULL,
          "sector_or_industry_symbol" TEXT NOT NULL,
          {score_defs},
          "diagnostic_payload_json" JSONB NOT NULL,
          PRIMARY KEY ("available_time", "sector_or_industry_symbol")
        )
        """
    )
    for column in generator.DIAGNOSTIC_SCORE_COLUMNS:
        cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} DOUBLE PRECISION")
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"diagnostic_payload_json\" JSONB NOT NULL DEFAULT '{{}}'::jsonb")
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in {"available_time", "sector_or_industry_symbol"}
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ({", ".join(quoted_columns)})
        VALUES ({", ".join(["%s"] * len(columns[:-1]))}, %s::jsonb)
        ON CONFLICT ("available_time", "sector_or_industry_symbol") DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(insert_sql, [*[row.get(column) for column in columns[:-1]], json.dumps(row.get("diagnostic_payload_json", {}), sort_keys=True, default=str)])


def generate_sql(
    *,
    database_url: str,
    feature_schema: str,
    feature_table: str,
    market_schema: str,
    market_table: str,
    target_schema: str,
    target_table: str,
    explainability_table: str,
    diagnostics_table: str,
    source_start: str | None,
    source_end: str | None,
    model_version: str,
) -> int:
    generator = _load_generator()
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            feature_rows = fetch_feature_rows(
                cursor,
                source_schema=feature_schema,
                source_table=feature_table,
                source_start=source_start,
                source_end=source_end,
            )
            market_rows = fetch_market_context_rows(
                cursor,
                source_schema=market_schema,
                source_table=market_table,
                source_start=source_start,
                source_end=source_end,
            )
            primary_rows = generator.generate_rows(feature_rows, market_rows, model_version=model_version)
            write_model_rows_sql(cursor, primary_rows, target_schema=target_schema, target_table=target_table)
            write_explainability_rows_sql(
                cursor,
                generator.build_explainability_rows(feature_rows, market_rows, model_version=model_version),
                target_schema=target_schema,
                target_table=explainability_table,
            )
            write_diagnostics_rows_sql(
                cursor,
                generator.build_diagnostics_rows(feature_rows, market_rows),
                target_schema=target_schema,
                target_table=diagnostics_table,
            )
            return len(primary_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default="trading_data")
    parser.add_argument("--feature-table", default="feature_02_sector_context")
    parser.add_argument("--market-schema", default="trading_model")
    parser.add_argument("--market-table", default="model_01_market_regime")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_02_sector_context")
    parser.add_argument("--explainability-table", help="Optional explainability artifact table. Defaults to <target-table>_explainability.")
    parser.add_argument("--diagnostics-table", help="Optional diagnostics artifact table. Defaults to <target-table>_diagnostics.")
    parser.add_argument("--source-start", help="Optional lower timestamp bound for feature and Layer 1 rows.")
    parser.add_argument("--source-end", help="Optional upper timestamp bound for feature and Layer 1 rows.")
    generator = _load_generator()
    parser.add_argument("--model-version", default=generator.MODEL_VERSION)
    args = parser.parse_args(argv)

    explainability_table = args.explainability_table or f"{args.target_table}_explainability"
    diagnostics_table = args.diagnostics_table or f"{args.target_table}_diagnostics"
    row_count = generate_sql(
        database_url=_database_url(args.database_url),
        feature_schema=args.feature_schema,
        feature_table=args.feature_table,
        market_schema=args.market_schema,
        market_table=args.market_table,
        target_schema=args.target_schema,
        target_table=args.target_table,
        explainability_table=explainability_table,
        diagnostics_table=diagnostics_table,
        source_start=args.source_start,
        source_end=args.source_end,
        model_version=args.model_version,
    )
    print(
        f"generated {row_count} rows into {args.target_schema}.{args.target_table} "
        f"with support artifacts {args.target_schema}.{explainability_table} and {args.target_schema}.{diagnostics_table}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

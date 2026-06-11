#!/usr/bin/env python3
"""Generate deterministic EventRiskGovernor rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from zoneinfo import ZoneInfo

from model_runtime.config import database_url_file

from model_governance.model_output_support import drop_absent_retired_horizon_columns, write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_10_event_risk_governor import MODEL_ID, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
ET = ZoneInfo("America/New_York")
JSON_COLUMNS = {"event_context_vector", "event_risk_governor_diagnostics"}
PRIMARY_KEY = ("event_context_vector_ref",)
EXPLAINABILITY_COLUMNS = {"event_context_vector"}
DIAGNOSTICS_COLUMNS = {"event_risk_governor_diagnostics"}
SOURCE_TABLE = "m06_residual_event_governance_data_acquisition"


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
    except ModuleNotFoundError as error:  # pragma: no cover
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
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("10_"):
        return "DOUBLE PRECISION"
    return "TEXT"


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = _parse_time(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET).isoformat()


def _fetch_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None, order_by: str) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("available_time < %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY {order_by}", params)
    return [dict(row) for row in cursor.fetchall()]


def _table_exists(cursor: Any, *, schema: str, table: str) -> bool:
    _quote_identifier(schema)
    _quote_identifier(table)
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"{schema}.{table}",))
    row = cursor.fetchone()
    if isinstance(row, Mapping):
        return row.get("table_ref") is not None
    if isinstance(row, Sequence):
        return bool(row and row[0] is not None)
    return False


def _fetch_target_context_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    explainability_table = f"{table}_explainability"
    if not _table_exists(cursor, schema=schema, table=explainability_table):
        return _fetch_rows(
            cursor,
            schema=schema,
            table=table,
            source_start=source_start,
            source_end=source_end,
            order_by="available_time ASC, target_candidate_id ASC",
        )
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('t."available_time" >= %s')
        params.append(source_start)
    if source_end:
        where.append('t."available_time" < %s')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT
          t.*,
          e."target_context_state",
          e."target_state_embedding",
          e."state_cluster_id"
        FROM {_qualified(schema, table)} AS t
        LEFT JOIN {_qualified(schema, explainability_table)} AS e
          ON e."target_candidate_id" = t."target_candidate_id"
         AND e."available_time"::timestamptz = t."available_time"::timestamptz
         AND e."model_version" = t."model_version"
        {where_sql}
        ORDER BY t."available_time" ASC, t."target_candidate_id" ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _fetch_event_source_rows(cursor: Any, *, schema: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    return _fetch_rows(
        cursor,
        schema=schema,
        table=SOURCE_TABLE,
        source_start=source_start,
        source_end=source_end,
        order_by="available_time ASC, event_id ASC",
    )


def _decision_rows(
    *,
    source_rows: Sequence[Mapping[str, Any]],
    source_03_rows: Sequence[Mapping[str, Any]],
    model_03_rows: Sequence[Mapping[str, Any]],
    model_09_rows: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    target_by_symbol_time: dict[tuple[str, str], Mapping[str, Any]] = {}
    source_by_candidate_time: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in source_03_rows:
        if row.get("symbol") and row.get("available_time"):
            target_by_symbol_time[(str(row["symbol"]).upper(), _iso(row["available_time"]))] = row
        if row.get("target_candidate_id") and row.get("available_time"):
            source_by_candidate_time[(str(row["target_candidate_id"]), _iso(row["available_time"]))] = row
    model_by_candidate_time: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in model_03_rows:
        if row.get("target_candidate_id") and row.get("available_time"):
            model_by_candidate_time[(str(row["target_candidate_id"]), _iso(row["available_time"]))] = row
    option_by_candidate_time = {
        (str(row.get("target_candidate_id")), _iso(row.get("available_time"))): row
        for row in model_09_rows
        if row.get("target_candidate_id") and row.get("available_time")
    }
    rows: list[dict[str, Any]] = []
    if not source_rows:
        for target_model in model_03_rows:
            candidate = str(target_model.get("target_candidate_id") or "")
            available = _iso(target_model.get("available_time"))
            if not candidate or not available:
                continue
            target_source = source_by_candidate_time.get((candidate, available), {})
            option_row = option_by_candidate_time.get((candidate, available), {})
            rows.append(
                {
                    "available_time": available,
                    "tradeable_time": _iso(target_model.get("tradeable_time") or available),
                    "target_candidate_id": candidate,
                    "symbol_for_join_only": target_source.get("symbol"),
                    "sector_type": target_source.get("sector_type"),
                    "market_context_state_ref": target_model.get("market_context_state_ref"),
                    "sector_context_state_ref": target_model.get("sector_context_state_ref"),
                    "target_context_state_ref": target_model.get("target_context_state_ref"),
                    "target_context_state": target_model.get("target_context_state"),
                    "underlying_action_plan_ref": option_row.get("underlying_action_plan_ref"),
                    "event_rows": [],
                }
            )
        return rows
    for event in source_rows:
        symbol = str(event.get("symbol") or "").upper()
        available = _iso(event.get("available_time"))
        target_source = target_by_symbol_time.get((symbol, available))
        if not target_source:
            continue
        candidate = str(target_source.get("target_candidate_id"))
        target_model = model_by_candidate_time.get((candidate, available))
        if not target_model:
            continue
        option_row = option_by_candidate_time.get((candidate, available), {})
        rows.append(
            {
                "available_time": available,
                "tradeable_time": available,
                "target_candidate_id": candidate,
                "symbol_for_join_only": symbol,
                "sector_type": event.get("sector_type"),
                "market_context_state_ref": target_model.get("market_context_state_ref"),
                "sector_context_state_ref": target_model.get("sector_context_state_ref"),
                "target_context_state_ref": target_model.get("target_context_state_ref"),
                "target_context_state": target_model.get("target_context_state"),
                "underlying_action_plan_ref": option_row.get("underlying_action_plan_ref"),
                "event_rows": [dict(event)],
            }
        )
    return rows


def _ensure_table(cursor: Any, *, target_schema: str, target_table: str, columns: Sequence[str]) -> None:
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    column_defs = ",\n          ".join(f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns)
    pk_sql = ", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_qualified(target_schema, target_table)} ({column_defs}, PRIMARY KEY ({pk_sql}))")
    for column in columns:
        cursor.execute(f"ALTER TABLE {_qualified(target_schema, target_table)} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


def _write_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    write_model_output_with_support(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        primary_key=PRIMARY_KEY,
        explainability_columns=EXPLAINABILITY_COLUMNS,
        diagnostics_columns=DIAGNOSTICS_COLUMNS,
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), encoding="utf-8")


def _database_model_rows(decisions: Sequence[Mapping[str, Any]], *, model_version: str) -> list[dict[str, Any]]:
    if not decisions:
        return []
    return generate_rows(decisions, model_version=model_version)


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            source_rows = _fetch_event_source_rows(cursor, schema="trading_data", source_start=source_start, source_end=source_end)
            source_03_rows = _fetch_rows(cursor, schema="trading_data", table="m03_target_state_vector_data_acquisition", source_start=source_start, source_end=source_end, order_by="available_time ASC, target_candidate_id ASC")
            model_03_rows = _fetch_target_context_rows(cursor, schema="trading_model", table="model_03_target_state_vector", source_start=source_start, source_end=source_end)
            model_09_rows = _fetch_rows(cursor, schema="trading_model", table="model_09_option_expression", source_start=source_start, source_end=source_end, order_by="available_time ASC, target_candidate_id ASC")
            decisions = _decision_rows(source_rows=source_rows, source_03_rows=source_03_rows, model_03_rows=model_03_rows, model_09_rows=model_09_rows)
            model_rows = _database_model_rows(decisions, model_version=model_version)
            if model_rows:
                _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
            else:
                drop_absent_retired_horizon_columns(cursor, schema=target_schema, table=target_table)
    if output_jsonl:
        _write_jsonl(output_jsonl, model_rows)
    return len(model_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_10_event_risk_governor")
    args = parser.parse_args(argv)
    if args.from_database:
        count = generate_from_database(database_url=_database_url(args.database_url), source_start=args.source_start, source_end=args.source_end, target_schema=args.target_schema, target_table=args.target_table, model_version=args.model_version, output_jsonl=args.output_jsonl)
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_10_event_risk_governor", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

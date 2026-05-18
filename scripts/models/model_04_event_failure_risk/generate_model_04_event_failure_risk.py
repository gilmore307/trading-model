#!/usr/bin/env python3
"""Generate deterministic EventFailureRiskModel rows from local JSON/JSONL or database rows."""
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

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_04_event_failure_risk import MODEL_ID, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
ET = ZoneInfo("America/New_York")
JSON_COLUMNS = {"event_failure_risk_vector", "event_failure_risk_diagnostics"}
PRIMARY_KEY = ("event_failure_risk_vector_ref",)


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
    if column.startswith("4_"):
        return "DOUBLE PRECISION" if column != "4_resolved_event_failure_risk_status" else "TEXT"
    return "TEXT"


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _ensure_table(cursor: Any, *, schema: str, table: str, rows: Sequence[Mapping[str, Any]]) -> None:
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema)}")
    columns = sorted({key for row in rows for key in row.keys()})
    if not columns:
        raise ValueError("no columns to create")
    definitions = [f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns]
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_qualified(schema, table)} ({', '.join(definitions)})")
    for column in columns:
        cursor.execute(f"ALTER TABLE {_qualified(schema, table)} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


def _insert_rows(cursor: Any, *, schema: str, table: str, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    columns = sorted({key for row in rows for key in row.keys()})
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(_quote_column_identifier(column) for column in columns)
    conflict_sql = ""
    if all(key in columns for key in PRIMARY_KEY):
        conflict_sql = " ON CONFLICT DO NOTHING"
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            if column in JSON_COLUMNS and value is not None:
                value = json.dumps(value, sort_keys=True)
            values.append(_jsonable(value))
        cursor.execute(f"INSERT INTO {_qualified(schema, table)} ({column_sql}) VALUES ({placeholders}){conflict_sql}", values)


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


def _fetch_table_rows(
    cursor: Any,
    *,
    schema: str,
    table: str,
    source_start: str | None,
    source_end: str | None,
    order_by: str,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY {order_by}", params)
    return [dict(row) for row in cursor.fetchall()]


def _fetch_target_context_rows(
    cursor: Any,
    *,
    schema: str,
    table: str,
    source_start: str | None,
    source_end: str | None,
) -> list[dict[str, Any]]:
    explainability_table = f"{table}_explainability"
    if not _table_exists(cursor, schema=schema, table=explainability_table):
        return _fetch_table_rows(
            cursor,
            schema=schema,
            table=table,
            source_start=source_start,
            source_end=source_end,
            order_by="available_time::timestamptz ASC, target_candidate_id ASC",
        )
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('t."available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('t."available_time"::timestamptz < %s::timestamptz')
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
        ORDER BY t."available_time"::timestamptz ASC, t."target_candidate_id" ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _payload_value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _neutral_input_rows_from_target_context(target_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    neutral_rows: list[dict[str, Any]] = []
    for row in target_rows:
        neutral_rows.append(
            {
                "available_time": row.get("available_time"),
                "tradeable_time": row.get("tradeable_time") or row.get("available_time"),
                "target_candidate_id": row.get("target_candidate_id"),
                "market_context_state_ref": row.get("market_context_state_ref"),
                "sector_context_state_ref": row.get("sector_context_state_ref"),
                "target_context_state_ref": row.get("target_context_state_ref") or row.get("target_state_vector_ref"),
                "target_context_state": _payload_value(row, "target_context_state", "target_state_vector"),
                "target_state_vector": _payload_value(row, "target_context_state", "target_state_vector"),
                "event_strategy_failure_gate_ref": None,
                "event_strategy_failure_gate": {
                    "gate_status": "not_present",
                    "review_decision": "no_reviewed_event_failure_risk",
                    "reason_codes": ["no_reviewed_event_strategy_failure_gate"],
                },
            }
        )
    return neutral_rows


def _merge_gate_rows_with_target_context(
    *,
    gate_rows: Sequence[Mapping[str, Any]],
    target_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    targets_by_key = {
        (str(row.get("target_candidate_id") or ""), str(row.get("available_time") or "")): row
        for row in target_rows
    }
    merged: list[dict[str, Any]] = []
    for gate in gate_rows:
        row = dict(gate)
        target = targets_by_key.get((str(row.get("target_candidate_id") or ""), str(row.get("available_time") or "")))
        if target is not None:
            row.setdefault("tradeable_time", target.get("tradeable_time") or target.get("available_time"))
            row.setdefault("market_context_state_ref", target.get("market_context_state_ref"))
            row.setdefault("sector_context_state_ref", target.get("sector_context_state_ref"))
            row.setdefault("target_context_state_ref", target.get("target_context_state_ref") or target.get("target_state_vector_ref"))
            row.setdefault("target_context_state", _payload_value(target, "target_context_state", "target_state_vector"))
            row.setdefault("target_state_vector", _payload_value(target, "target_context_state", "target_state_vector"))
        merged.append(row)
    return merged


def _fetch_input_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    target_context_schema: str,
    target_context_table: str,
    source_start: str | None,
    source_end: str | None,
) -> list[dict[str, Any]]:
    target_rows = _fetch_target_context_rows(
        cursor,
        schema=target_context_schema,
        table=target_context_table,
        source_start=source_start,
        source_end=source_end,
    )
    if not _table_exists(cursor, schema=source_schema, table=source_table):
        return _neutral_input_rows_from_target_context(target_rows)
    gate_rows = _fetch_table_rows(
        cursor,
        schema=source_schema,
        table=source_table,
        source_start=source_start,
        source_end=source_end,
        order_by="available_time::timestamptz ASC, target_candidate_id ASC",
    )
    if not gate_rows:
        return _neutral_input_rows_from_target_context(target_rows)
    return _merge_gate_rows_with_target_context(gate_rows=gate_rows, target_rows=target_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to fixture rows.")
    parser.add_argument("--output-jsonl", "--output", dest="output_jsonl", type=Path, help="Optional local output path.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--write-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-schema", default="trading_model")
    parser.add_argument("--source-table", default="event_strategy_failure_gate")
    parser.add_argument("--target-context-schema", default="trading_model")
    parser.add_argument("--target-context-table", default="model_03_target_state_vector")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_04_event_failure_risk")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database or args.write_database:
        psycopg, dict_row = _load_psycopg()
        with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                input_rows = (
                    _fetch_input_rows(
                        cursor,
                        source_schema=args.source_schema,
                        source_table=args.source_table,
                        target_context_schema=args.target_context_schema,
                        target_context_table=args.target_context_table,
                        source_start=args.source_start,
                        source_end=args.source_end,
                    )
                    if args.from_database
                    else (read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE])
                )
                rows = generate_rows(input_rows, model_version=args.model_version)
                if args.from_database or args.write_database:
                    _ensure_table(cursor, schema=args.target_schema, table=args.target_table, rows=rows)
                    _insert_rows(cursor, schema=args.target_schema, table=args.target_table, rows=rows)
                conn.commit()
        if args.output_jsonl or not args.from_database:
            write_rows(rows, args.output_jsonl)
        if args.from_database:
            print(f"generated {len(rows)} rows into {args.target_schema}.{args.target_table}")
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_04_event_failure_risk", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

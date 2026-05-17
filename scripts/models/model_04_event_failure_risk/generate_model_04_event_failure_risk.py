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

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_04_event_failure_risk import MODEL_ID, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
ET = ZoneInfo("America/New_York")
JSON_COLUMNS = {"event_failure_risk_vector", "event_failure_risk_diagnostics"}
PRIMARY_KEY = ("event_failure_risk_vector_ref",)


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
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


def _fetch_source_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY available_time::timestamptz ASC", params)
    return [dict(row) for row in cursor.fetchall()]


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
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_04_event_failure_risk")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database or args.write_database:
        psycopg, dict_row = _load_psycopg()
        with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                input_rows = _fetch_source_rows(cursor, schema=args.source_schema, table=args.source_table, source_start=args.source_start, source_end=args.source_end) if args.from_database else (read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE])
                rows = generate_rows(input_rows, model_version=args.model_version)
                if args.write_database:
                    _ensure_table(cursor, schema=args.target_schema, table=args.target_table, rows=rows)
                    _insert_rows(cursor, schema=args.target_schema, table=args.target_table, rows=rows)
                conn.commit()
        write_rows(rows, args.output_jsonl)
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_04_event_failure_risk", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

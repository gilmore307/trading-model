#!/usr/bin/env python3
"""Generate deterministic model_03_target_state_vector rows from feature rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from models.model_03_target_state_vector import generator

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"target_context_state", "target_state_embedding", "state_quality_diagnostics"}
PRIMARY_KEY = ("target_candidate_id", "available_time", "model_version")


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
    if column in JSON_COLUMNS:
        return "JSONB"
    if column in {"available_time", "tradeable_time"}:
        return "TEXT"
    if column.startswith("3_"):
        return "DOUBLE PRECISION"
    return "TEXT"


def fetch_feature_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("available_time < %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"SELECT * FROM {_qualified(source_schema, source_table)}{where_sql} ORDER BY available_time ASC, target_candidate_id ASC",
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


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
    columns = list(rows[0].keys())
    _ensure_table(cursor, target_schema=target_schema, target_table=target_table, columns=columns)
    quoted_columns = [_quote_column_identifier(column) for column in columns]
    placeholders = ["%s::jsonb" if column in JSON_COLUMNS else "%s" for column in columns]
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
    for row in rows:
        values = [json.dumps(row.get(column), sort_keys=True, default=str) if column in JSON_COLUMNS else row.get(column) for column in columns]
        cursor.execute(insert_sql, values)


def generate_from_database(
    *,
    database_url: str,
    feature_schema: str,
    feature_table: str,
    target_schema: str,
    target_table: str,
    source_start: str | None,
    source_end: str | None,
    model_version: str,
    output: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            feature_rows = fetch_feature_rows(cursor, source_schema=feature_schema, source_table=feature_table, source_start=source_start, source_end=source_end)
            model_rows = generator.generate_rows(feature_rows, model_version=model_version)
            write_model_rows_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
    if output:
        _write_jsonl(output, model_rows)
    return len(model_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path, help="JSON/JSONL feature_03_target_state_vector rows")
    parser.add_argument("--output", type=Path, help="Optional JSONL output path. Defaults to stdout for file mode.")
    parser.add_argument("--model-version", default=generator.MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true", help="Read feature rows from PostgreSQL and write model rows to PostgreSQL.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default="trading_data")
    parser.add_argument("--feature-table", default="feature_03_target_state_vector")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_03_target_state_vector")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database:
        row_count = generate_from_database(
            database_url=_database_url(args.database_url),
            feature_schema=args.feature_schema,
            feature_table=args.feature_table,
            target_schema=args.target_schema,
            target_table=args.target_table,
            source_start=args.source_start,
            source_end=args.source_end,
            model_version=args.model_version,
            output=args.output,
        )
        print(f"generated {row_count} rows into {args.target_schema}.{args.target_table}")
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

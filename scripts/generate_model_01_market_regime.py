#!/usr/bin/env python3
"""Generate model_01_market_regime rows from derived SQL features."""
from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_generator():
    return importlib.import_module("model_outputs.model_01_market_regime.generator")


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


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def fetch_derived_rows(
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
        f"SELECT * FROM {_qualified(source_schema, source_table)}{where_sql} ORDER BY snapshot_time ASC",
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def write_model_rows_sql(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
) -> None:
    if not rows:
        return
    generator = _load_generator()
    columns = list(generator.OUTPUT_COLUMNS)
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ PRIMARY KEY
        )
        """
    )
    for column in columns:
        if column == "available_time":
            continue
        cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {_quote_identifier(column)} DOUBLE PRECISION")

    quoted_columns = [_quote_identifier(column) for column in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    update_sql = ", ".join(
        f"{_quote_identifier(column)} = EXCLUDED.{_quote_identifier(column)}"
        for column in columns
        if column != "available_time"
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ({", ".join(quoted_columns)})
        VALUES ({placeholders})
        ON CONFLICT ("available_time") DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(insert_sql, [row.get(column) for column in columns])


def generate_sql(
    *,
    database_url: str,
    source_schema: str,
    source_table: str,
    target_schema: str,
    target_table: str,
    source_start: str | None,
    source_end: str | None,
    lookback: int,
    min_history: int,
) -> int:
    generator = _load_generator()
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            feature_rows = fetch_derived_rows(
                cursor,
                source_schema=source_schema,
                source_table=source_table,
                source_start=source_start,
                source_end=source_end,
            )
            rows = generator.generate_rows(feature_rows, lookback=lookback, min_history=min_history)
            write_model_rows_sql(cursor, rows, target_schema=target_schema, target_table=target_table)
            return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--source-schema", default="trading_data")
    parser.add_argument("--source-table", default="feature_01_market_regime")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_01_market_regime")
    parser.add_argument("--source-start", help="Optional lower timestamp bound for derived rows. Include enough lookback for rolling factors.")
    parser.add_argument("--source-end", help="Optional upper timestamp bound for derived rows.")
    generator = _load_generator()
    parser.add_argument("--lookback", type=int, default=generator.STANDARDIZATION.lookback)
    parser.add_argument("--min-history", type=int, default=generator.STANDARDIZATION.min_history)
    args = parser.parse_args(argv)

    row_count = generate_sql(
        database_url=_database_url(args.database_url),
        source_schema=args.source_schema,
        source_table=args.source_table,
        target_schema=args.target_schema,
        target_table=args.target_table,
        source_start=args.source_start,
        source_end=args.source_end,
        lookback=args.lookback,
        min_history=args.min_history,
    )
    print(f"generated {row_count} rows into {args.target_schema}.{args.target_table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Create or emit generic trading_model governance and evaluation table DDL."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from model_governance.schema import (
    DEFAULT_SCHEMA,
    TABLE_NAMES,
    create_governance_schema_sql,
    ensure_model_governance_schema,
)

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
DEFAULT_SQL_OUTPUT = Path("storage/sql/model_governance_schema.sql")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for governance schema creation; install psycopg[binary].") from error
    return psycopg


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _sql_text(schema: str) -> str:
    statements = [statement.strip() for statement in create_governance_schema_sql(schema)]
    return "\n\n".join(statement.rstrip(";") + ";" for statement in statements) + "\n"


def _write_sql(path: Path, *, schema: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_sql_text(schema), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help=f"Target schema, default: {DEFAULT_SCHEMA}")
    parser.add_argument(
        "--sql-output",
        type=Path,
        default=DEFAULT_SQL_OUTPUT,
        help=f"Local SQL output path for dry-run DDL, default: {DEFAULT_SQL_OUTPUT}",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually connect to PostgreSQL and create the tables. Not used by default during development.",
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL URL. Only read when --apply is set; defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.",
    )
    args = parser.parse_args(argv)

    if not args.apply:
        _write_sql(args.sql_output, schema=args.schema)
        print(f"wrote dry-run DDL for {len(TABLE_NAMES)} model governance tables to {args.sql_output}")
        print("DRY RUN ONLY: no database connection was opened and no rows/tables were written.")
        return 0

    psycopg = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url)) as conn:
        with conn.cursor() as cursor:
            ensure_model_governance_schema(cursor, schema=args.schema)

    print(f"ensured {len(TABLE_NAMES)} model governance tables in {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

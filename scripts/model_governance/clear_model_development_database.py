#!/usr/bin/env python3
"""Clear trading-model-owned development database objects.

This script is intentionally scoped to the ``trading_model`` schema. It must not
be generalized to drop OpenClaw/system tables or other component schemas.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from model_governance.schema import DEFAULT_SCHEMA, quote_identifier

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
CONFIRM_TOKEN = "clear-trading-model-development-database"


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def cleanup_sql(schema: str = DEFAULT_SCHEMA) -> str:
    q_schema = quote_identifier(schema)
    return f"DROP SCHEMA IF EXISTS {q_schema} CASCADE;\nCREATE SCHEMA {q_schema};\n"


def _run_psql(database_url: str, sql: str) -> None:
    subprocess.run(
        ["psql", database_url, "-v", "ON_ERROR_STOP=1", "-q"],
        input=f"BEGIN;\n{sql}\nCOMMIT;\n",
        text=True,
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help=f"Target schema, default: {DEFAULT_SCHEMA}")
    parser.add_argument("--dry-run", action="store_true", help="Print cleanup SQL without connecting to PostgreSQL.")
    parser.add_argument("--confirm", help=f"Required for destructive cleanup. Must equal {CONFIRM_TOKEN!r}.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    args = parser.parse_args(argv)

    sql = cleanup_sql(args.schema)
    if args.dry_run:
        print(sql, end="")
        print("-- DRY RUN ONLY: no database connection was opened and no schema was dropped.")
        return 0

    if args.confirm != CONFIRM_TOKEN:
        raise SystemExit(f"refusing destructive cleanup; pass --confirm {CONFIRM_TOKEN}")

    _run_psql(_database_url(args.database_url), sql)
    print(f"cleared development schema {args.schema!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

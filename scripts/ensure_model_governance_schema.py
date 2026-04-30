#!/usr/bin/env python3
"""Create generic trading_model governance and evaluation tables."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from model_governance.schema import DEFAULT_SCHEMA, TABLE_NAMES, ensure_model_governance_schema

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help=f"Target schema, default: {DEFAULT_SCHEMA}")
    args = parser.parse_args(argv)

    psycopg = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url)) as conn:
        with conn.cursor() as cursor:
            ensure_model_governance_schema(cursor, schema=args.schema)

    print(f"ensured {len(TABLE_NAMES)} model governance tables in {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

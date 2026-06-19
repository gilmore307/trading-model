#!/usr/bin/env python3
"""Audit trading_model model output/support tables for empty columns."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from model_runtime.config import database_url_file
from model_governance.model_output_audit import (
    CURRENT_MODEL_OUTPUT_TABLES,
    audit_database,
)

DEFAULT_DB_URL_FILE = database_url_file()


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


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for model-output table audit; install psycopg[binary].") from error
    return psycopg, dict_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--schema", default="trading_model")
    parser.add_argument("--sample-limit", type=int, default=5000)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--print-cleanup-sql", action="store_true", help="Print review-only DROP COLUMN candidates after the JSON audit.")
    args = parser.parse_args(argv)
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            audit = audit_database(cursor, schema=args.schema, tables=CURRENT_MODEL_OUTPUT_TABLES, sample_limit=args.sample_limit)
    payload = json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n"
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.print_cleanup_sql:
        for statement in audit.get("cleanup_sql_review_required", []):
            print(statement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

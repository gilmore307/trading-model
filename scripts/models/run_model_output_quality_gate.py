#!/usr/bin/env python3
"""Run the model-output table quality gate."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from model_runtime.config import database_url_file
from model_governance.model_output_audit import audit_database, dump_audit_json
from model_governance.model_output_quality_gate import evaluate_quality_gate

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
        raise SystemExit("psycopg is required for model-output quality gate; install psycopg[binary].") from error
    return psycopg, dict_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--schema", default="trading_model")
    parser.add_argument("--sample-limit", type=int, default=5000)
    parser.add_argument("--output-json", type=Path, help="Write gate result JSON here.")
    parser.add_argument("--audit-json", type=Path, help="Optionally write the underlying audit JSON here.")
    parser.add_argument("--strict-support", action="store_true", help="Treat explainability/diagnostic all-null gaps as blockers.")
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after writing/printing the gate result.")
    args = parser.parse_args(argv)

    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            audit = audit_database(cursor, schema=args.schema, sample_limit=args.sample_limit)
    gate = evaluate_quality_gate(audit, strict_support=args.strict_support)

    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(dump_audit_json(audit), encoding="utf-8")
    payload = dump_audit_json(gate)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if gate["status"] == "blocked" and not args.report_only:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

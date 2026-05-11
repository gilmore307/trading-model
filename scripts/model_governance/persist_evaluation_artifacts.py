#!/usr/bin/env python3
"""Persist model evaluation artifact table rows into trading_model governance tables.

This script is idempotent and model-side only. It writes dataset/evaluation/metric
evidence rows; it never creates manager promotion decisions, activates model
configs, performs provider calls, or touches broker/account state.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from model_governance.common.sql import DEFAULT_SCHEMA
from model_governance.evaluation.persistence import load_artifact_tables, persist_artifact_tables


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_json", type=Path, help="Evaluation artifact JSON with table rows, or a payload containing a 'tables' object.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count rows without connecting or writing.")
    args = parser.parse_args(argv)

    tables = load_artifact_tables(args.artifact_json)
    counts = {table: len(rows) for table, rows in tables.items()}
    if args.dry_run:
        print(json.dumps({"dry_run": True, "artifact_json": str(args.artifact_json), "row_counts": counts}, indent=2, sort_keys=True))
        return 0
    persisted = persist_artifact_tables(tables, database_url_value=args.database_url, schema=args.schema)
    print(json.dumps({"dry_run": False, "artifact_json": str(args.artifact_json), "persisted_row_counts": persisted}, indent=2, sort_keys=True))
    print("MODEL EVIDENCE ONLY: no manager decision, model activation, provider call, broker execution, or account mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

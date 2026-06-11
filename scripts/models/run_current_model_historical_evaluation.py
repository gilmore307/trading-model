#!/usr/bin/env python3
"""Run a read-only historical evaluation pass for the current M01-M06 chain."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from model_governance.historical_current_chain_evaluation import (
    load_historical_rows_from_database,
    run_historical_current_chain_evaluation,
)
from model_runtime.config import database_url_file, model_storage_root

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
        raise SystemExit("psycopg is required for historical model evaluation; install psycopg[binary].") from error
    return psycopg, dict_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--start-time", default="2017-01-03T00:00:00-05:00")
    parser.add_argument("--end-time", default="2017-04-01T00:00:00-04:00")
    parser.add_argument("--limit", type=int, default=750)
    parser.add_argument("--per-month-limit", type=int, default=250)
    parser.add_argument("--label-horizon-days", type=int, default=7)
    parser.add_argument("--run-id")
    parser.add_argument("--skip-baseline-training", action="store_true")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--receipt-only", action="store_true")
    args = parser.parse_args(argv)

    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            rows = load_historical_rows_from_database(
                cursor,
                start_time=args.start_time,
                end_time=args.end_time,
                limit=args.limit,
                per_month_limit=args.per_month_limit,
                label_horizon_days=args.label_horizon_days,
            )
    artifact = run_historical_current_chain_evaluation(
        rows,
        run_id=args.run_id,
        train_baseline=not args.skip_baseline_training,
    )
    payload = artifact["receipt"] if args.receipt_only else artifact
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def default_output_path(run_id: str) -> Path:
    return model_storage_root() / "current_model_historical_evaluation" / run_id / "current_model_historical_evaluation.json"


if __name__ == "__main__":
    raise SystemExit(main())

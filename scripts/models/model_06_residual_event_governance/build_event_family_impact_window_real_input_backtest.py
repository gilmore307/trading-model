#!/usr/bin/env python3
"""Build real-input EventRiskGovernor impact-window backtest artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from models.model_06_residual_event_governance.event_family_impact_window_real_inputs import (
    DEFAULT_END_DATE_EXCLUSIVE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_START_DATE,
    DEFAULT_STORAGE_SECRET_ALIAS,
    DEFAULT_SYMBOLS,
    build_real_input_backtest_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--database-url", help="Explicit PostgreSQL DSN. Defaults to the trading storage secret alias.")
    parser.add_argument("--storage-secret-alias", default=DEFAULT_STORAGE_SECRET_ALIAS)
    parser.add_argument("--source-root", type=Path, help="Monthly source-data root. Defaults to data_storage_root()/monthly_backfill.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE.isoformat())
    parser.add_argument("--end-date-exclusive", default=DEFAULT_END_DATE_EXCLUSIVE.isoformat())
    parser.add_argument("--symbol", action="append", dest="symbols", help="Price symbol to export; repeatable.")
    parser.add_argument("--max-breaking-news-dates", type=int, default=24)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_real_input_backtest_artifacts(
        output_dir=args.output_dir,
        database_url=args.database_url,
        storage_secret_alias=args.storage_secret_alias,
        source_root=args.source_root,
        start_date=date.fromisoformat(args.start_date),
        end_date_exclusive=date.fromisoformat(args.end_date_exclusive),
        symbols=tuple(args.symbols or DEFAULT_SYMBOLS),
        max_breaking_news_dates=args.max_breaking_news_dates,
    )
    if args.print_json:
        json.dump(result.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

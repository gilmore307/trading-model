#!/usr/bin/env python3
"""Build all-family real-input Layer 10 impact-window calibration evidence."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_real_inputs import (
    DEFAULT_ALL_FAMILY_OUTPUT_DIR,
    DEFAULT_END_DATE_EXCLUSIVE,
    DEFAULT_START_DATE,
    DEFAULT_STORAGE_SECRET_ALIAS,
    DEFAULT_SYMBOLS,
    build_all_family_real_input_backtest_artifacts,
)


def _date_arg(value: str) -> date:
    return date.fromisoformat(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ALL_FAMILY_OUTPUT_DIR)
    parser.add_argument("--database-url")
    parser.add_argument("--storage-secret-alias", default=DEFAULT_STORAGE_SECRET_ALIAS)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--start-date", type=_date_arg, default=DEFAULT_START_DATE)
    parser.add_argument("--end-date-exclusive", type=_date_arg, default=DEFAULT_END_DATE_EXCLUSIVE)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--max-dates-per-family", type=int, default=80)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_all_family_real_input_backtest_artifacts(
        output_dir=args.output_dir,
        database_url=args.database_url,
        storage_secret_alias=args.storage_secret_alias,
        source_root=args.source_root,
        start_date=args.start_date,
        end_date_exclusive=args.end_date_exclusive,
        symbols=tuple(args.symbols),
        max_dates_per_family=args.max_dates_per_family,
    )
    if args.print_json:
        json.dump(result.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

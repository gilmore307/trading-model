#!/usr/bin/env python3
"""Build the EventRiskGovernor event-family impact-window backtest."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_backtest import (
    DEFAULT_OUTPUT_DIR,
    build_real_input_event_family_impact_window_backtest,
    build_sample_event_family_impact_window_backtest,
    write_backtest,
    write_event_family_impact_window_backtest_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--event-csv", type=Path, action="append", dest="event_csvs", help="Reviewed event input CSV. Repeatable.")
    parser.add_argument("--bar-csv", type=Path, action="append", dest="bar_csvs", help="Point-in-time price bar CSV. Repeatable.")
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.event_csvs or args.bar_csvs:
        if not args.event_csvs or not args.bar_csvs:
            raise SystemExit("--event-csv and --bar-csv must be provided together for real-input runs")
        backtest = build_real_input_event_family_impact_window_backtest(
            event_paths=tuple(args.event_csvs),
            bar_paths=tuple(args.bar_csvs),
        )
    else:
        backtest = build_sample_event_family_impact_window_backtest()
    write_event_family_impact_window_backtest_artifacts(backtest, args.output_dir)
    if args.print_json:
        write_backtest(backtest, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

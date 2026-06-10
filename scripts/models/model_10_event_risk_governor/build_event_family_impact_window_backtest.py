#!/usr/bin/env python3
"""Build the EventRiskGovernor event-family impact-window sample backtest."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_10_event_risk_governor.event_family_impact_window_backtest import (
    DEFAULT_OUTPUT_DIR,
    build_sample_event_family_impact_window_backtest,
    write_backtest,
    write_event_family_impact_window_backtest_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backtest = build_sample_event_family_impact_window_backtest()
    write_event_family_impact_window_backtest_artifacts(backtest, args.output_dir)
    if args.print_json:
        write_backtest(backtest, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

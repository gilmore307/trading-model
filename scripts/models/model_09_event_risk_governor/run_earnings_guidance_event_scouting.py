#!/usr/bin/env python3
"""Run earnings/guidance event-family scouting controls from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_09_event_risk_governor.earnings_guidance_scouting import StudyInputs, run_study


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abnormal-windows", type=Path, required=True)
    parser.add_argument("--control-windows", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, action="append", required=True, help="Reviewed release_calendar.csv artifact. Repeatable.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbols", default="AAPL,MSFT,NVDA,AMD,JPM,XOM,CVX,LLY,PFE,COIN,TSLA,RKLB")
    args = parser.parse_args()
    report = run_study(
        StudyInputs(
            abnormal_windows_path=args.abnormal_windows,
            control_windows_path=args.control_windows,
            calendar_paths=tuple(args.calendar),
            output_dir=args.output_dir,
            target_symbols=tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()),
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"canonical_earnings_shell_window_count={report['canonical_earnings_shell_window_count']}")
    print(f"verified_non_earnings_control_window_count={report['verified_non_earnings_control_window_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

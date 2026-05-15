#!/usr/bin/env python3
"""Run event-alone earnings/guidance scheduled-shell scouting from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_event_alone import EventAloneInputs, run_event_alone_study


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", type=Path, action="append", required=True, help="Reviewed release_calendar.csv artifact. Repeatable.")
    parser.add_argument("--equity-bars", type=Path, action="append", required=True, help="Reviewed equity_bar.csv artifact. Repeatable.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbols", required=True, help="Comma-separated target symbols.")
    parser.add_argument("--max-controls-per-event", type=int, default=3)
    parser.add_argument("--control-exclusion-days", type=int, default=3)
    args = parser.parse_args()
    report = run_event_alone_study(
        EventAloneInputs(
            calendar_paths=tuple(args.calendar),
            equity_bar_paths=tuple(args.equity_bars),
            output_dir=args.output_dir,
            target_symbols=tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()),
            max_controls_per_event=args.max_controls_per_event,
            control_exclusion_days=args.control_exclusion_days,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"event_window_count={report['event_window_count']}")
    print(f"control_window_count={report['control_window_count']}")
    print(f"paired_event_count={report['paired_event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

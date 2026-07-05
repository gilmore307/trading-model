#!/usr/bin/env python3
"""Build a read-only tradable-time return distribution surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from models.return_distribution_surface import (
    ALLOWED_SOURCE_TABLES,
    bucket_regular_session_closes,
    build_tradable_time_label_rows,
    fit_tradable_time_distribution_surface,
    load_pit_bars,
    write_surface_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-02-01")
    parser.add_argument("--source", choices=sorted(ALLOWED_SOURCE_TABLES), default="m01")
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--anchor-minutes", type=int, default=10)
    parser.add_argument("--max-trading-minutes", type=int, default=1170)
    parser.add_argument("--fit-mode", choices=("baseline", "context"), default="context")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    rows = load_pit_bars(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        source=args.source,
        timeframe=args.timeframe,
    )
    closes = bucket_regular_session_closes(rows, bucket_minutes=args.anchor_minutes, symbol=args.symbol)
    label_rows = build_tradable_time_label_rows(
        closes,
        anchor_minutes=args.anchor_minutes,
        max_trading_minutes=args.max_trading_minutes,
    )
    result = fit_tradable_time_distribution_surface(label_rows, fit_mode=args.fit_mode)
    summary = write_surface_artifacts(
        output_dir=output_dir,
        symbol=args.symbol,
        source_table=ALLOWED_SOURCE_TABLES[args.source],
        source_timeframe=args.timeframe if args.source == "m01" else None,
        source_range={"start": args.start, "end_exclusive": args.end},
        anchor_minutes=args.anchor_minutes,
        bar_rows_loaded=len(rows),
        bucket_close_count=len(closes),
        label_rows=label_rows,
        result=result,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build CPI/inflation local event-control association readiness artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.cpi_inflation_association_readiness import (
    DEFAULT_CONTROL_WINDOW_DAYS,
    DEFAULT_DATA_ROOT,
    DEFAULT_HORIZONS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRICE_SYMBOLS,
    build_cpi_inflation_association_readiness,
    write_readiness,
    write_readiness_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT, help="trading-data repository root.")
    parser.add_argument("--price-symbol", action="append", dest="price_symbols", help="ETF/security symbol to label; may be repeated.")
    parser.add_argument("--horizon", action="append", type=int, dest="horizons", help="Forward horizon in trading days; may be repeated.")
    parser.add_argument("--control-window-days", type=int, default=DEFAULT_CONTROL_WINDOW_DAYS, help="Trading-day window around each event for local controls.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    readiness = build_cpi_inflation_association_readiness(
        data_root=args.data_root,
        price_symbols=tuple(args.price_symbols or DEFAULT_PRICE_SYMBOLS),
        horizons=tuple(args.horizons or DEFAULT_HORIZONS),
        control_window_days=args.control_window_days,
    )
    write_readiness_artifacts(readiness, args.output_dir)
    write_readiness(readiness, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

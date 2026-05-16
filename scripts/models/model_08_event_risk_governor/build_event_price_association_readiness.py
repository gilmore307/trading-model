#!/usr/bin/env python3
"""Build a safe local event-price association readiness batch."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_08_event_risk_governor.event_price_association_readiness import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_DATA_ROOT,
    DEFAULT_FAMILY_KEYS,
    DEFAULT_MONTH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRICE_SYMBOLS,
    build_event_price_association_readiness_batch,
    write_batch,
    write_batch_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH, help="Event-family batch catalog JSON.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT, help="trading-data repository root.")
    parser.add_argument("--month", default=DEFAULT_MONTH, help="Local month to inspect, YYYY-MM.")
    parser.add_argument("--family", action="append", dest="families", help="Family key to include; may be repeated.")
    parser.add_argument("--price-symbol", action="append", dest="price_symbols", help="Price symbol for macro labels; may be repeated.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    batch = build_event_price_association_readiness_batch(
        catalog_path=args.catalog,
        data_root=args.data_root,
        month=args.month,
        family_keys=tuple(args.families or DEFAULT_FAMILY_KEYS),
        price_symbols=tuple(args.price_symbols or DEFAULT_PRICE_SYMBOLS),
    )
    write_batch_artifacts(batch, args.output_dir)
    write_batch(batch, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

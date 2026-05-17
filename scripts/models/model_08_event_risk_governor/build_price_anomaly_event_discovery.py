#!/usr/bin/env python3
"""Build reverse price-anomaly/event-family discovery artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_08_event_risk_governor.price_anomaly_event_discovery import (
    ANOMALY_Z_THRESHOLD,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_ROOT,
    DEFAULT_BAR_ROOT,
    EVENT_MONTH,
    EVENT_WINDOW_DAYS,
    build_price_anomaly_event_discovery,
    write_discovery,
    write_price_anomaly_event_discovery_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-root", type=Path, default=DEFAULT_BAR_ROOT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--month", default=EVENT_MONTH)
    parser.add_argument("--anomaly-z-threshold", type=float, default=ANOMALY_Z_THRESHOLD)
    parser.add_argument("--event-window-days", type=int, default=EVENT_WINDOW_DAYS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    discovery = build_price_anomaly_event_discovery(
        bar_root=args.bar_root,
        source_root=args.source_root,
        month=args.month,
        anomaly_z_threshold=args.anomaly_z_threshold,
        event_window_days=args.event_window_days,
    )
    write_price_anomaly_event_discovery_artifacts(discovery, args.output_dir)
    if args.print_json:
        write_discovery(discovery, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

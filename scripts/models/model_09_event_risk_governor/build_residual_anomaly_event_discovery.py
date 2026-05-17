#!/usr/bin/env python3
"""Build Layer 8 residual-anomaly event discovery artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.residual_anomaly_event_discovery import (
    DEFAULT_EVALUATION_MONTH,
    DEFAULT_EVENT_WINDOW_DAYS,
    DEFAULT_MODEL_RUNTIME_ROOT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_ROOT,
    MIN_RESIDUAL_SEVERITY,
    build_residual_anomaly_event_discovery,
    write_discovery,
    write_residual_anomaly_event_discovery_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_MODEL_RUNTIME_ROOT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--evaluation-month", default=DEFAULT_EVALUATION_MONTH)
    parser.add_argument("--event-window-days", type=int, default=DEFAULT_EVENT_WINDOW_DAYS)
    parser.add_argument("--min-residual-severity", type=float, default=MIN_RESIDUAL_SEVERITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    discovery = build_residual_anomaly_event_discovery(
        runtime_root=args.runtime_root,
        source_root=args.source_root,
        evaluation_month=args.evaluation_month,
        event_window_days=args.event_window_days,
        min_residual_severity=args.min_residual_severity,
    )
    write_residual_anomaly_event_discovery_artifacts(discovery, args.output_dir)
    if args.print_json:
        write_discovery(discovery, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

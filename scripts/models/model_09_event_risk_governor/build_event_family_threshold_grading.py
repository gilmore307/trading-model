#!/usr/bin/env python3
"""Build EventRiskGovernor event-family threshold/grading queue artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_family_threshold_grading import (
    DEFAULT_ASSOCIATION_DIR,
    DEFAULT_OUTPUT_DIR,
    build_event_family_threshold_grading,
    write_event_family_threshold_grading_artifacts,
    write_grading,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--association-dir", type=Path, default=DEFAULT_ASSOCIATION_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    grading = build_event_family_threshold_grading(association_dir=args.association_dir)
    write_event_family_threshold_grading_artifacts(grading, args.output_dir)
    if args.print_json:
        write_grading(grading, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

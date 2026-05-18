#!/usr/bin/env python3
"""Build local empirical coverage/readiness for all EventRiskGovernor families."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_08_event_risk_governor.event_family_empirical_coverage import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRECONDITION_PATH,
    DEFAULT_TRADING_DATA_ROOT,
    build_event_family_empirical_coverage,
    write_coverage,
    write_empirical_coverage_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precondition", type=Path, default=DEFAULT_PRECONDITION_PATH, help="Precondition completion JSON.")
    parser.add_argument("--trading-data-root", type=Path, default=DEFAULT_TRADING_DATA_ROOT, help="Local trading-data repo root.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    coverage = build_event_family_empirical_coverage(
        precondition_path=args.precondition,
        trading_data_root=args.trading_data_root,
    )
    write_empirical_coverage_artifacts(coverage, args.output_dir)
    write_coverage(coverage, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

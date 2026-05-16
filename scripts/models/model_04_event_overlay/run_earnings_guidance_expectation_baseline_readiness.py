#!/usr/bin/env python3
"""Run point-in-time earnings/guidance expectation baseline readiness scout."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_expectation_baseline import (
    ExpectationBaselineInputs,
    run_expectation_baseline_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpretation-rows", type=Path, required=True)
    parser.add_argument("--baseline-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_expectation_baseline_readiness(
        ExpectationBaselineInputs(
            interpretation_rows_path=args.interpretation_rows,
            baseline_manifest_path=args.baseline_manifest,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"accepted_baseline_set_event_count={report['accepted_baseline_set_event_count']}")
    print(f"missing_baseline_event_count={report['missing_baseline_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

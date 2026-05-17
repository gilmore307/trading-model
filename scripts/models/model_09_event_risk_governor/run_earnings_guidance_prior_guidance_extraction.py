#!/usr/bin/env python3
"""Extract prior-company-guidance baseline context from official prior documents."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_09_event_risk_governor.earnings_guidance_prior_guidance_extraction import (
    PriorGuidanceExtractionInputs,
    run_prior_guidance_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-rows", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_prior_guidance_extraction(
        PriorGuidanceExtractionInputs(
            coverage_rows_path=args.coverage_rows,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"accepted_prior_guidance_baseline_event_count={report['accepted_prior_guidance_baseline_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

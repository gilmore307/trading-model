#!/usr/bin/env python3
"""Audit prior official filings as earnings/guidance baseline source candidates."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_prior_official_baseline import (
    PriorOfficialBaselineInputs,
    run_prior_official_baseline_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpretation-rows", type=Path, required=True)
    parser.add_argument("--sec-submission-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lookback-days", type=int, default=180)
    args = parser.parse_args()
    report = run_prior_official_baseline_audit(
        PriorOfficialBaselineInputs(
            interpretation_rows_path=args.interpretation_rows,
            sec_submission_root=args.sec_submission_root,
            output_dir=args.output_dir,
            lookback_days=args.lookback_days,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"candidate_source_event_count={report['candidate_source_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

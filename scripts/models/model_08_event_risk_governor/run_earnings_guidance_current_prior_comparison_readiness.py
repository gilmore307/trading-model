#!/usr/bin/env python3
"""Assess current-vs-prior earnings/guidance comparison readiness."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_current_prior_comparison_readiness import (
    CurrentPriorComparisonReadinessInputs,
    run_current_prior_comparison_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-event-rows", type=Path, required=True)
    parser.add_argument("--prior-span-rows", type=Path, required=True)
    parser.add_argument("--current-review-rows", type=Path, required=True)
    parser.add_argument("--current-review-spans", type=Path, required=True)
    parser.add_argument("--result-event-rows", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_current_prior_comparison_readiness(
        CurrentPriorComparisonReadinessInputs(
            prior_event_rows_path=args.prior_event_rows,
            prior_span_rows_path=args.prior_span_rows,
            current_review_rows_path=args.current_review_rows,
            current_review_spans_path=args.current_review_spans,
            result_event_rows_path=args.result_event_rows,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"accepted_prior_guidance_baseline_event_count={report['accepted_prior_guidance_baseline_event_count']}")
    print(f"current_comparable_guidance_event_count={report['current_comparable_guidance_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

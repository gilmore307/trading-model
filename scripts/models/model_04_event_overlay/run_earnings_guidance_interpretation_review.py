#!/usr/bin/env python3
"""Run conservative earnings/guidance interpretation review from candidate spans."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_interpretation_review import (
    GuidanceInterpretationReviewInputs,
    run_guidance_interpretation_review,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-rows", type=Path, required=True)
    parser.add_argument("--candidate-spans", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_guidance_interpretation_review(
        GuidanceInterpretationReviewInputs(
            candidate_rows_path=args.candidate_rows,
            candidate_spans_path=args.candidate_spans,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"partial_guidance_context_event_count={report['partial_guidance_context_event_count']}")
    print(f"expectation_baseline_count={report['expectation_baseline_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

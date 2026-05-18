#!/usr/bin/env python3
"""Run earnings/guidance official result-artifact scout from local SEC artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_result_artifact_scout import ResultArtifactInputs, run_result_artifact_scout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-windows", type=Path, required=True)
    parser.add_argument("--sec-submission", type=Path, action="append", required=True, help="Local sec_submission.csv artifact. Repeatable.")
    parser.add_argument("--sec-company-fact", type=Path, action="append", required=True, help="Local sec_company_fact.csv artifact. Repeatable.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_result_artifact_scout(
        ResultArtifactInputs(
            event_windows_path=args.event_windows,
            sec_submission_paths=tuple(args.sec_submission),
            sec_company_fact_paths=tuple(args.sec_company_fact),
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"event_count={report['event_count']}")
    print(f"official_result_artifact_count={report['official_result_artifact_count']}")
    print(f"partial_result_interpretation_count={report['partial_result_interpretation_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

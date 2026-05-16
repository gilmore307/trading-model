#!/usr/bin/env python3
"""Run earnings/guidance official-artifact coverage scout from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_artifact_coverage import (
    GuidanceArtifactCoverageInputs,
    run_guidance_artifact_coverage_scout,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpreted-events", type=Path, required=True)
    parser.add_argument("--result-filings", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sec-filing-document-metadata", type=Path, action="append", default=[])
    parser.add_argument("--accepted-guidance-interpretation", type=Path)
    args = parser.parse_args()
    report = run_guidance_artifact_coverage_scout(
        GuidanceArtifactCoverageInputs(
            interpreted_events_path=args.interpreted_events,
            result_filings_path=args.result_filings,
            output_dir=args.output_dir,
            sec_filing_document_metadata_paths=tuple(args.sec_filing_document_metadata),
            accepted_guidance_interpretation_path=args.accepted_guidance_interpretation,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"result_filing_reference_count={report['result_filing_reference_count']}")
    print(f"local_official_document_text_artifact_count={report['local_official_document_text_artifact_count']}")
    print(f"accepted_guidance_interpretation_count={report['accepted_guidance_interpretation_count']}")
    print(f"expectation_baseline_count={report['expectation_baseline_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

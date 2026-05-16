#!/usr/bin/env python3
"""Check prior official guidance candidate document-text coverage."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_prior_official_document_coverage import (
    PriorOfficialDocumentCoverageInputs,
    run_prior_official_document_coverage,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-rows", type=Path, required=True)
    parser.add_argument("--document-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_prior_official_document_coverage(
        PriorOfficialDocumentCoverageInputs(
            source_rows_path=args.source_rows,
            document_root=args.document_root,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"prior_official_document_text_present_event_count={report['prior_official_document_text_present_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

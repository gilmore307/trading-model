#!/usr/bin/env python3
"""Extract prior-company-guidance baselines from official earnings exhibits."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_prior_guidance_exhibit_extraction import (
    PriorGuidanceExhibitExtractionInputs,
    run_prior_guidance_exhibit_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-keys-dir", type=Path, required=True)
    parser.add_argument("--document-text-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_prior_guidance_exhibit_extraction(
        PriorGuidanceExhibitExtractionInputs(
            task_keys_dir=args.task_keys_dir,
            document_text_root=args.document_text_root,
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

#!/usr/bin/env python3
"""Run earnings/guidance official-guidance readiness scout from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_readiness_scout import (
    GuidanceReadinessInputs,
    run_guidance_readiness_scout,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpreted-events", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_guidance_readiness_scout(
        GuidanceReadinessInputs(
            interpreted_events_path=args.interpreted_events,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"official_guidance_interpretation_count={report['official_guidance_interpretation_count']}")
    print(f"expectation_baseline_count={report['expectation_baseline_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

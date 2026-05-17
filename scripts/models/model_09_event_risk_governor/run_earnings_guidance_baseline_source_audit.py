#!/usr/bin/env python3
"""Audit existing calendar artifacts as earnings/guidance baseline sources."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_09_event_risk_governor.earnings_guidance_baseline_source_audit import (
    BaselineSourceAuditInputs,
    run_baseline_source_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpretation-rows", type=Path, required=True)
    parser.add_argument("--calendar-artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_baseline_source_audit(
        BaselineSourceAuditInputs(
            interpretation_rows_path=args.interpretation_rows,
            calendar_artifact_root=args.calendar_artifact_root,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"event_count={report['event_count']}")
    print(f"matched_event_count={report['matched_event_count']}")
    print(f"eps_forecast_present_event_count={report['eps_forecast_present_event_count']}")
    print(f"accepted_pit_baseline_event_count={report['accepted_pit_baseline_event_count']}")
    print(f"signed_direction_ready_count={report['signed_direction_ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

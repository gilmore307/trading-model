#!/usr/bin/env python3
"""Run option-abnormality non-earnings saturation study from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.option_abnormality_non_earnings_saturation import (
    NonEarningsSaturationInputs,
    run_non_earnings_saturation_study,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--option-events", type=Path, required=True)
    parser.add_argument("--canonical-earnings", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_non_earnings_saturation_study(
        NonEarningsSaturationInputs(
            option_events_path=args.option_events,
            canonical_earnings_path=args.canonical_earnings,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"non_earnings_symbol_date_count={report['non_earnings_symbol_date_count']}")
    print(f"non_earnings_verified_no_abnormality_count={report['non_earnings_verified_no_abnormality_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

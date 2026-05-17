#!/usr/bin/env python3
"""Run earnings/guidance plus option-abnormality split scout from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_09_event_risk_governor.earnings_option_abnormality_split_scout import EarningsOptionSplitInputs, run_earnings_option_split_scout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-earnings", type=Path, required=True)
    parser.add_argument("--option-events", type=Path, required=True)
    parser.add_argument("--option-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_earnings_option_split_scout(
        EarningsOptionSplitInputs(
            canonical_earnings_path=args.canonical_earnings,
            option_events_path=args.option_events,
            option_report_path=args.option_report,
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"option_covered_earnings_count={report['option_covered_earnings_count']}")
    print(f"with_option_abnormality={report['earnings_with_verified_option_abnormality_count']}")
    print(f"without_option_abnormality={report['earnings_with_verified_no_option_abnormality_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

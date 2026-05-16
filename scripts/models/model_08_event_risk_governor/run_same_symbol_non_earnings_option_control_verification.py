#!/usr/bin/env python3
"""Run same-symbol non-earnings option-control verification from local artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_08_event_risk_governor.same_symbol_non_earnings_option_control_verification import (
    SameSymbolNonEarningsOptionControlInputs,
    summarize_same_symbol_non_earnings_option_controls,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-earnings", type=Path, required=True)
    parser.add_argument("--option-matrix-root", type=Path, required=True)
    parser.add_argument("--option-events", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--control-exclusion-days", type=int, default=3)
    args = parser.parse_args()
    report = summarize_same_symbol_non_earnings_option_controls(
        SameSymbolNonEarningsOptionControlInputs(
            canonical_earnings_path=args.canonical_earnings,
            option_matrix_root=args.option_matrix_root,
            option_events_path=args.option_events,
            output_dir=args.output_dir,
            control_exclusion_days=args.control_exclusion_days,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"provider_calls_performed_by_study={report['provider_calls_performed_by_study']}")
    print(f"provider_calls_referenced_from_option_matrix_receipts={report['provider_calls_referenced_from_option_matrix_receipts']}")
    print(f"same_symbol_non_earnings_window_count={report['same_symbol_non_earnings_window_count']}")
    print(f"same_symbol_non_earnings_verified_no_abnormality_count={report['same_symbol_non_earnings_verified_no_abnormality_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

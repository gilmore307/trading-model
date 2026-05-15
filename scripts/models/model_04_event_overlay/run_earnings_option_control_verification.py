#!/usr/bin/env python3
"""Summarize earnings option-abnormality control verification probes."""
from __future__ import annotations

import argparse
from pathlib import Path

from models.model_04_event_overlay.earnings_option_control_verification import (
    EarningsOptionControlVerificationInputs,
    summarize_earnings_option_control_verification,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-earnings", type=Path, required=True)
    parser.add_argument("--existing-option-events", type=Path, required=True)
    parser.add_argument("--contract-probes", type=Path, required=True)
    parser.add_argument("--equity-bar", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = summarize_earnings_option_control_verification(
        EarningsOptionControlVerificationInputs(
            canonical_earnings_path=args.canonical_earnings,
            existing_option_events_path=args.existing_option_events,
            contract_probe_path=args.contract_probes,
            equity_bar_paths=tuple(args.equity_bar),
            output_dir=args.output_dir,
        )
    )
    print(f"wrote {args.output_dir}")
    print(f"status={report['status']}")
    print(f"provider_calls_performed_by_study={report['provider_calls_performed_by_study']}")
    print(f"provider_calls_referenced_from_probe={report['provider_calls_referenced_from_probe']}")
    print(f"status_counts={report['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the accepted EventRiskGovernor closeout report without side effects."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_model_closeout import build_event_model_closeout_report, write_report, write_report_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, help="Optional path for the closeout report JSON artifact.")
    args = parser.parse_args(argv)

    report = build_event_model_closeout_report()
    if args.output_json:
        write_report_file(report, args.output_json)
    write_report(report, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

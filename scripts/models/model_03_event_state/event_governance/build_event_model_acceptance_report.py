#!/usr/bin/env python3
"""Build the accepted M03 event-state governance acceptance report without side effects."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_03_event_state.event_governance.event_model_acceptance import build_event_model_acceptance_report, write_report, write_report_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, help="Optional path for the acceptance report JSON artifact.")
    args = parser.parse_args(argv)

    report = build_event_model_acceptance_report()
    if args.output_json:
        write_report_file(report, args.output_json)
    write_report(report, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build all event-family scouting packets/preconditions before final judgment."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_family_precondition_completion import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_CLOSEOUT_PATH,
    DEFAULT_OUTPUT_DIR,
    build_event_family_precondition_completion,
    write_completion,
    write_precondition_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH, help="Event-family batch catalog JSON.")
    parser.add_argument("--closeout", type=Path, default=DEFAULT_CLOSEOUT_PATH, help="Remaining closeout JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    completion = build_event_family_precondition_completion(catalog_path=args.catalog, closeout_path=args.closeout)
    write_precondition_artifacts(completion, args.output_dir)
    write_completion(completion, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

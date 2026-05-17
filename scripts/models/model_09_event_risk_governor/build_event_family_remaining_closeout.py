#!/usr/bin/env python3
"""Build the safe local remaining event-family closeout artifact."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_family_remaining_closeout import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_OUTPUT_DIR,
    build_event_family_remaining_closeout,
    write_batch,
    write_closeout_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH, help="Event-family batch catalog JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    batch = build_event_family_remaining_closeout(catalog_path=args.catalog)
    write_closeout_artifacts(batch, args.output_dir)
    write_batch(batch, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

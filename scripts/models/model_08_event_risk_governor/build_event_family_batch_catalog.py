#!/usr/bin/env python3
"""Build the fine-grained event-family batch catalog without side effects."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_08_event_risk_governor.event_family_batch_catalog import (
    DEFAULT_OUTPUT_DIR,
    build_event_family_batch_catalog,
    write_catalog,
    write_catalog_artifacts,
    write_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="trading-model repository root for evidence-ref checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for JSON/CSV catalog artifacts.")
    parser.add_argument("--json", action="store_true", help="Print full catalog JSON instead of summary JSON.")
    args = parser.parse_args(argv)

    catalog = build_event_family_batch_catalog(root=args.root)
    output_dir = args.output_dir if args.output_dir.is_absolute() else args.root / args.output_dir
    write_catalog_artifacts(catalog, output_dir)
    if args.json:
        write_catalog(catalog, output=sys.stdout)
    else:
        write_summary(catalog, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

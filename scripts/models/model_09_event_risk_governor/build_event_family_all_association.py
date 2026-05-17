#!/usr/bin/env python3
"""Build local all-family event/price association measurements."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_09_event_risk_governor.event_family_all_association import (
    DEFAULT_BAR_ROOT,
    DEFAULT_COVERAGE_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_ROOT,
    build_event_family_all_association,
    write_association,
    write_event_family_all_association_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE_PATH)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--bar-root", type=Path, default=DEFAULT_BAR_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    association = build_event_family_all_association(
        coverage_path=args.coverage,
        source_root=args.source_root,
        bar_root=args.bar_root,
    )
    write_event_family_all_association_artifacts(association, args.output_dir)
    write_association(association, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

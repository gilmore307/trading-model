#!/usr/bin/env python3
"""Build the final EventRiskGovernor posture judgment from local evidence."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from models.model_08_event_risk_governor.event_layer_final_judgment import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_OUTPUT_DIR,
    build_event_layer_final_judgment,
    write_event_layer_final_judgment_artifacts,
    write_judgment,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE_PATH, help="Event-family empirical coverage JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output artifact directory.")
    args = parser.parse_args(argv)

    judgment = build_event_layer_final_judgment(coverage_path=args.coverage)
    write_event_layer_final_judgment_artifacts(judgment, args.output_dir)
    write_judgment(judgment, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

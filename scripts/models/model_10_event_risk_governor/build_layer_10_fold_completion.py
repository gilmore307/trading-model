#!/usr/bin/env python3
"""Build fold-scoped Layer 10 event-family completion evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models.model_10_event_risk_governor.fold_completion import (
    DEFAULT_ACCEPTANCE_PATH,
    DEFAULT_ASSOCIATION_PATH,
    DEFAULT_CATALOG_PATH,
    DEFAULT_COVERAGE_PATH,
    DEFAULT_FOLD_ID,
    DEFAULT_IMPACT_WINDOW_SUMMARY_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRECONDITION_PATH,
    DEFAULT_REPLAY_RUN_ID,
    DEFAULT_REPLAY_SUMMARY_PATH,
    build_layer_10_fold_completion,
    write_layer_10_fold_completion_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--acceptance", type=Path, default=DEFAULT_ACCEPTANCE_PATH)
    parser.add_argument("--precondition", type=Path, default=DEFAULT_PRECONDITION_PATH)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE_PATH)
    parser.add_argument("--association", type=Path, default=DEFAULT_ASSOCIATION_PATH)
    parser.add_argument("--impact-window-summary", type=Path, default=DEFAULT_IMPACT_WINDOW_SUMMARY_PATH)
    parser.add_argument("--replay-summary", type=Path, default=DEFAULT_REPLAY_SUMMARY_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fold-id", default=DEFAULT_FOLD_ID)
    parser.add_argument("--replay-run-id", default=DEFAULT_REPLAY_RUN_ID)
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    completion = build_layer_10_fold_completion(
        catalog_path=args.catalog,
        acceptance_path=args.acceptance,
        precondition_path=args.precondition,
        coverage_path=args.coverage,
        association_path=args.association,
        impact_window_summary_path=args.impact_window_summary,
        replay_summary_path=args.replay_summary,
        fold_id=args.fold_id,
        replay_run_id=args.replay_run_id,
    )
    write_layer_10_fold_completion_artifacts(completion, args.output_dir)
    if args.print_json:
        json.dump(completion.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

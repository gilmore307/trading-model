#!/usr/bin/env python3
"""Build Layer 4 input rows from accepted M06 focus-pool replay evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models.model_04_event_failure_risk.m06_residual_event_governance_focus_pool_inputs import (
    build_layer4_focus_pool_input_rows,
    read_csv,
    read_jsonl,
    write_jsonl,
)

DEFAULT_REPLAY_ROWS = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "event_family_impact_window_all_family_replay_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z/"
    "decision_event_overlay_rows.jsonl"
)
DEFAULT_GATE_MATRIX = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "m06_residual_event_governance_fold_completion_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z/"
    "m06_residual_event_governance_family_gate_matrix.csv"
)
DEFAULT_OUTPUT = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "layer_04_focus_pool_inputs_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z/"
    "layer_04_focus_pool_input_rows.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-rows", type=Path, default=DEFAULT_REPLAY_ROWS)
    parser.add_argument("--gate-matrix", type=Path, default=DEFAULT_GATE_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print-summary", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_layer4_focus_pool_input_rows(
        replay_overlay_rows=read_jsonl(args.replay_rows),
        gate_matrix_rows=read_csv(args.gate_matrix),
    )
    write_jsonl(args.output, rows)
    if args.print_summary:
        json.dump(
            {
                "output": str(args.output),
                "input_rows": len(rows),
                "source_replay_rows": str(args.replay_rows),
                "source_gate_matrix": str(args.gate_matrix),
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

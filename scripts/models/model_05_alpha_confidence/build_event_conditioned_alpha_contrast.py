#!/usr/bin/env python3
"""Build a diagnostic Layer 5 contrast for Layer 4 event-conditioned features."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from models.model_05_alpha_confidence.event_conditioned_contrast import (
    DIAGNOSTIC_SCOPE,
    build_labeled_focus_pool_rows,
    run_event_conditioned_alpha_contrast,
)

DEFAULT_LAYER4_ROWS = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "layer_04_focus_pool_inputs_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z/"
    "model_04_event_failure_risk_rows.jsonl"
)
DEFAULT_LAYER10_OVERLAY_ROWS = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "event_family_impact_window_all_family_replay_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z/"
    "decision_event_overlay_rows.jsonl"
)
DEFAULT_OUTPUT_DIR = Path(
    "/root/projects/trading-storage/storage/03_model_artifacts/"
    "layer_05_event_conditioned_alpha_contrast_20260610/"
    "fold_2016-01_2016-06/model_group_replay_20260609T060059Z"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer4-rows-jsonl", type=Path, default=DEFAULT_LAYER4_ROWS)
    parser.add_argument("--layer10-overlay-jsonl", type=Path, default=DEFAULT_LAYER10_OVERLAY_ROWS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--horizon", default="1D", choices=("10min", "1h", "1D", "1W"))
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--return-scale", type=float, default=0.02)
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    args = parser.parse_args()

    layer4_rows = _read_jsonl(args.layer4_rows_jsonl)
    layer10_overlay_rows = _read_jsonl(args.layer10_overlay_jsonl)
    labeled_rows = build_labeled_focus_pool_rows(layer4_rows, layer10_overlay_rows, horizon=args.horizon)
    contrast = run_event_conditioned_alpha_contrast(
        labeled_rows,
        horizon=args.horizon,
        train_fraction=args.train_fraction,
        return_scale=args.return_scale,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    predictions = contrast.pop("predictions")
    baseline_model_artifact = contrast.pop("baseline_model_artifact")
    event_conditioned_model_artifact = contrast.pop("event_conditioned_model_artifact")
    contrast["artifact_paths"] = {
        "summary": str(args.output_dir / "event_conditioned_alpha_contrast_summary.json"),
        "predictions": str(args.output_dir / "event_conditioned_alpha_contrast_predictions.jsonl"),
        "baseline_model_artifact": str(args.output_dir / "baseline_after_cost_alpha_model.json"),
        "event_conditioned_model_artifact": str(args.output_dir / "event_conditioned_after_cost_alpha_model.json"),
    }
    contrast["source_paths"] = {
        "layer4_rows_jsonl": str(args.layer4_rows_jsonl),
        "layer10_overlay_jsonl": str(args.layer10_overlay_jsonl),
    }
    contrast["safety_boundary"] = {
        "scope": DIAGNOSTIC_SCOPE,
        "provider_calls": 0,
        "sql_writes": 0,
        "training_activation": False,
        "broker_or_account_mutation": False,
        "artifact_deletion": False,
    }

    _write_json(args.output_dir / "event_conditioned_alpha_contrast_summary.json", contrast)
    _write_jsonl(args.output_dir / "event_conditioned_alpha_contrast_predictions.jsonl", predictions)
    _write_json(args.output_dir / "baseline_after_cost_alpha_model.json", baseline_model_artifact)
    _write_json(args.output_dir / "event_conditioned_after_cost_alpha_model.json", event_conditioned_model_artifact)

    print(json.dumps(contrast, indent=2, sort_keys=True))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            loaded = json.loads(line)
            if not isinstance(loaded, Mapping):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(dict(loaded))
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

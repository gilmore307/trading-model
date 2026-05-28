#!/usr/bin/env python3
"""Train a direct after-cost Layer 5 alpha score artifact from local rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from model_governance.local_layer_scripts import read_rows, write_payload
from models.model_05_alpha_confidence.training import train_after_cost_alpha_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-jsonl", type=Path, required=True, help="JSON/JSONL rows containing point-in-time Layer 5 inputs plus after-cost labels.")
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path, required=True, help="Where to write the trained artifact.")
    parser.add_argument("--horizon", default="1W")
    parser.add_argument("--label-field", help="Optional explicit realized after-cost return label field.")
    parser.add_argument("--return-scale", type=float, default=0.02)
    parser.add_argument("--iterations", type=int, default=700)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.001)
    args = parser.parse_args(argv)

    rows = read_rows(args.training_jsonl)
    artifact = train_after_cost_alpha_model(
        rows,
        horizon=args.horizon,
        label_field=args.label_field,
        return_scale=args.return_scale,
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    write_payload(_json_safe(artifact), args.output_json)
    return 0


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(nested) for nested in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())

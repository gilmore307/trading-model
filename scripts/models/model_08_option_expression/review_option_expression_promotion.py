#!/usr/bin/env python3
"""Conservative OptionExpressionModel local promotion-review wrapper.

The wrapper reviews a local evaluation summary and always refuses activation.
Production approval remains gated by the accepted model-governance substrate,
real labels/metrics, baselines, stability, leakage checks, and explicit review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_governance.local_layer_scripts import conservative_review, write_payload
from models.model_08_option_expression import MODEL_ID, MODEL_SURFACE


def _load_summary(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "summary" in payload:
        return dict(payload["summary"])
    if isinstance(payload, dict):
        return dict(payload)
    raise ValueError("evaluation summary JSON must be an object")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, help="Optional output path for the review decision.")
    args = parser.parse_args(argv)

    summary = _load_summary(args.evaluation_summary_json)
    summary.setdefault("model_id", MODEL_ID)
    summary.setdefault("model_surface", MODEL_SURFACE)
    decision = conservative_review(summary)
    write_payload(decision, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build TargetStateVectorModel promotion evidence from local JSON/JSONL rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from models.model_03_target_state_vector import evaluation, generator


def _read_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("feature_rows") or payload.get("model_rows") or []
    return [dict(row) for row in payload]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path, required=True)
    parser.add_argument("--model-rows", type=Path, help="Optional model rows; generated from feature rows when omitted")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args(argv)
    feature_rows = _read_rows(args.feature_rows)
    model_rows = _read_rows(args.model_rows) if args.model_rows else generator.generate_rows(feature_rows)
    artifacts = evaluation.build_evaluation_artifacts(feature_rows=feature_rows, model_rows=model_rows)
    payload = {"tables": artifacts.as_table_rows(), "threshold_summary": evaluation.summarize_threshold_results(artifacts.eval_metrics)}
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

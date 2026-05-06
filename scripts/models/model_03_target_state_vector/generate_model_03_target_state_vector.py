#!/usr/bin/env python3
"""Generate deterministic model_03_target_state_vector rows from feature rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from models.model_03_target_state_vector import generator


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
    parser.add_argument("--feature-rows", type=Path, required=True, help="JSON/JSONL feature_03_target_state_vector rows")
    parser.add_argument("--output", type=Path, help="Optional JSONL output path. Defaults to stdout.")
    parser.add_argument("--model-version", default=generator.MODEL_VERSION)
    args = parser.parse_args(argv)
    rows = generator.generate_rows(_read_rows(args.feature_rows), model_version=args.model_version)
    lines = "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(lines, encoding="utf-8")
    else:
        print(lines, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

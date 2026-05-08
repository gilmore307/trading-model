#!/usr/bin/env python3
"""Generate deterministic OptionExpressionModel rows from local JSON/JSONL inputs.

This is a stable local entrypoint. It supports JSON/JSONL input
and deliberately does not activate production promotion state.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_08_option_expression import MODEL_ID, MODEL_SURFACE, MODEL_VERSION


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    args = parser.parse_args(argv)

    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_08_option_expression", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

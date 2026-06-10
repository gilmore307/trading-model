#!/usr/bin/env python3
"""Generate EventStateModel rows from local JSON/JSONL rows."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_03_event_state import MODEL_SURFACE, MODEL_VERSION

COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"event_state_vector", "event_state_diagnostics"}
TEXT_3_COLUMNS: set[str] = set()


def _column_type(column: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(column):
        raise ValueError(f"unsafe SQL column identifier: {column!r}")
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("3_"):
        return "TEXT" if column in TEXT_3_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/NDJSON or JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    args = parser.parse_args(argv)

    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_03_event_state", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

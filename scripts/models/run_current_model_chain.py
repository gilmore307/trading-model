#!/usr/bin/env python3
"""Run the current M01-M06 deterministic model chain and emit a local receipt."""
from __future__ import annotations

import argparse
from pathlib import Path

from model_governance.current_chain import run_current_chain
from model_governance.local_layer_scripts import read_rows, write_payload


def _read_input_payload(path: Path | None) -> dict:
    if path is None:
        return {}
    rows = read_rows(path)
    if len(rows) != 1:
        raise ValueError("--input-json must contain exactly one JSON object or one-row JSON array")
    return rows[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, help="Optional one-row JSON/JSONL object overriding default fixture payload fields.")
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path, help="Optional path for the full receipt, evaluations, and rows.")
    parser.add_argument("--receipt-only", action="store_true", help="Emit only the top-level receipt instead of rows and evaluations.")
    parser.add_argument("--evidence-source", default="fixture_current_chain")
    args = parser.parse_args(argv)

    payload = run_current_chain(input_payload=_read_input_payload(args.input_json), evidence_source=args.evidence_source)
    output = payload["receipt"] if args.receipt_only else payload
    write_payload(output, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

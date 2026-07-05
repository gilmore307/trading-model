#!/usr/bin/env python3
"""Run the current M01-M05 deterministic model chain and emit a local receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_governance.current_chain import run_current_chain
from model_governance.local_layer_scripts import read_rows, write_payload


def _read_input_payload(path: Path | None) -> dict:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and not any(
        key in raw for key in ("rows", "input_rows", "model_rows", "outcome_rows", "labels")
    ):
        return raw
    rows = read_rows(path)
    if len(rows) != 1:
        raise ValueError("--input-json must contain exactly one JSON object or one-row JSON array")
    return rows[0]


def _read_surface_summary(path: Path | None) -> dict | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--return-surface-summary-json must contain one JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, help="Optional one-row JSON/JSONL object overriding default fixture payload fields.")
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path, help="Optional path for the full receipt, evaluations, and rows.")
    parser.add_argument("--receipt-only", action="store_true", help="Emit only the top-level receipt instead of rows and evaluations.")
    parser.add_argument("--evidence-source", default="fixture_current_chain")
    parser.add_argument("--return-surface-summary-json", type=Path, help="Optional tradable-time return distribution surface summary to pass into M04.")
    args = parser.parse_args(argv)

    input_payload = _read_input_payload(args.input_json)
    surface_summary = _read_surface_summary(args.return_surface_summary_json)
    if surface_summary is not None:
        input_payload["tradable_time_return_distribution_surface_summary"] = surface_summary
    payload = run_current_chain(input_payload=input_payload, evidence_source=args.evidence_source)
    output = payload["receipt"] if args.receipt_only else payload
    write_payload(output, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build local AlphaConfidenceModel labels and evaluation summary.

This entrypoint is intentionally local/fixture-safe. It checks inference rows for
label leakage where the layer exposes a leakage checker, joins supplied outcome
rows into offline labels, and emits a conservative summary. It does not write
promotion-governance rows or activate configs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from model_governance.local_layer_scripts import (
    FIXTURE_INPUT_ROWS,
    evaluate_layer,
    fixture_outcome_rows,
    generate_layer,
    read_rows,
    write_payload,
)
from models.model_05_alpha_confidence import MODEL_ID, MODEL_SURFACE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-jsonl", type=Path, help="Local JSONL/JSON model rows. Defaults to generated fixture model rows.")
    parser.add_argument("--input-jsonl", type=Path, help="Optional input rows used to generate model rows when --model-jsonl is absent.")
    parser.add_argument("--outcome-jsonl", type=Path, help="Local JSONL/JSON realized outcome rows. Defaults to fixture outcomes built from model refs.")
    parser.add_argument("--output-json", type=Path, help="Optional output path for summary and labels.")
    parser.add_argument("--evidence-source", default="fixture_or_local_jsonl")
    args = parser.parse_args(argv)

    if args.model_jsonl:
        model_rows = read_rows(args.model_jsonl)
    else:
        input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
        model_rows = generate_layer("models.model_05_alpha_confidence", input_rows)
    outcome_rows = read_rows(args.outcome_jsonl) if args.outcome_jsonl else fixture_outcome_rows(MODEL_SURFACE, model_rows)
    payload = evaluate_layer(
        module_name="models.model_05_alpha_confidence",
        label_builder_name="build_alpha_confidence_labels",
        model_rows=model_rows,
        outcome_rows=outcome_rows,
        layer_number=5,
        model_surface=MODEL_SURFACE,
        model_id=MODEL_ID,
        evidence_source=args.evidence_source,
    )
    write_payload(payload, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

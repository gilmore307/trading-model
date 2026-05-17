#!/usr/bin/env python3
"""Review EventFailureRiskModel promotion evidence conservatively."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_governance.local_layer_scripts import conservative_review, write_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-summary-json", required=True, type=Path)
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.evaluation_summary_json.read_text(encoding="utf-8"))
    summary = payload.get("summary", payload)
    write_payload(conservative_review(summary), args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

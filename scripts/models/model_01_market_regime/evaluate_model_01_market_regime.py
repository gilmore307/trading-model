#!/usr/bin/env python3
"""Dry-run MarketRegimeModel evaluation harness.

This script never connects to PostgreSQL and never writes a database. It builds
in-memory rows for the generic model governance/evaluation tables and prints a
summary, so development experiments cannot leak into production storage.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from models.model_01_market_regime.evaluation import build_evaluation_artifacts, summarize_artifacts

ET = ZoneInfo("America/New_York")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(parsed)
    return rows


def _fixture_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start = datetime(2026, 1, 2, 16, 0, tzinfo=ET)
    feature_rows: list[dict[str, object]] = []
    model_rows: list[dict[str, object]] = []
    for index in range(12):
        available_time = (start + timedelta(days=index)).isoformat()
        one_day_return = ((index % 5) - 2) / 100.0
        five_day_return = (index - 6) / 200.0
        feature_rows.append(
            {
                "snapshot_time": available_time,
                "spy_return_1d": one_day_return,
                "spy_return_5d": five_day_return,
            }
        )
        trend = (index - 5.5) / 6.0
        stress = (5.5 - index) / 8.0
        model_rows.append(
            {
                "available_time": available_time,
                "1_price_behavior_factor": trend / 1.5,
                "1_trend_certainty_factor": trend,
                "1_capital_flow_factor": stress / 3,
                "1_sentiment_factor": trend,
                "1_valuation_pressure_factor": stress / 4,
                "1_fundamental_strength_factor": trend / 2,
                "1_macro_environment_factor": stress / 5,
                "1_market_structure_factor": stress / 2,
                "1_risk_stress_factor": stress,
                "1_transition_pressure": abs(trend) / 10,
                "1_data_quality_score": 1.0,
            }
        )
    return feature_rows, model_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-jsonl", type=Path, help="Optional local JSONL feature rows. Must include snapshot_time and label source columns.")
    parser.add_argument("--model-jsonl", type=Path, help="Optional local JSONL model rows. Must include available_time and factor columns.")
    parser.add_argument("--output-json", type=Path, help="Optional local output path for generated dry-run artifacts.")
    parser.add_argument("--print-artifacts", action="store_true", help="Print full generated artifacts instead of summary only.")
    parser.add_argument("--model-config-hash", help="Optional config hash to stamp into snapshot/eval run rows.")
    args = parser.parse_args(argv)

    if bool(args.feature_jsonl) != bool(args.model_jsonl):
        raise SystemExit("--feature-jsonl and --model-jsonl must be supplied together")

    if args.feature_jsonl and args.model_jsonl:
        feature_rows = _read_jsonl(args.feature_jsonl)
        model_rows = _read_jsonl(args.model_jsonl)
    else:
        feature_rows, model_rows = _fixture_rows()

    artifacts = build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        model_config_hash=args.model_config_hash,
    )
    payload = artifacts.as_table_rows() if args.print_artifacts else summarize_artifacts(artifacts)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output_json:
        args.output_json.write_text(text, encoding="utf-8")
        print(f"wrote dry-run evaluation artifacts to {args.output_json}")
    else:
        print(text, end="")
    print("DRY RUN ONLY: no database connection was opened and no rows were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

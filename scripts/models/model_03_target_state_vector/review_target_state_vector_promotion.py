#!/usr/bin/env python3
"""Conservative TargetStateVectorModel promotion review wrapper.

Local/fixture evidence is reviewed but not approved automatically. Production
approval requires real-data evidence, passing thresholds, and a separate accepted
review path before activation.
"""
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
    parser.add_argument("--model-rows", type=Path)
    parser.add_argument("--evidence-source", default="fixture_or_local_jsonl")
    args = parser.parse_args(argv)
    feature_rows = _read_rows(args.feature_rows)
    model_rows = _read_rows(args.model_rows) if args.model_rows else generator.generate_rows(feature_rows)
    artifacts = evaluation.build_evaluation_artifacts(feature_rows=feature_rows, model_rows=model_rows, evidence_source=args.evidence_source)
    summary = evaluation.summarize_threshold_results(artifacts.eval_metrics)
    decision = "deferred"
    reasons = []
    if args.evidence_source != "real_database_evaluation":
        reasons.append("fixture_or_local_evidence_must_defer")
    if summary["promotion_gate_state"] != "passed":
        reasons.extend(summary["failed_thresholds"])
    print(json.dumps({"review_decision": decision, "reason_codes": reasons or ["requires_explicit_agent_approval_before_activation"], "threshold_summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

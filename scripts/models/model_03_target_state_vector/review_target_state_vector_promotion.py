#!/usr/bin/env python3
"""Conservative TargetStateVectorModel promotion review wrapper."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from models.model_03_target_state_vector import evaluation, generator


def _read_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("feature_rows") or payload.get("model_rows") or []
    return [dict(row) for row in payload]


def _summary_from_evaluation_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("threshold_summary") if isinstance(payload, dict) else None
    if not isinstance(summary, dict):
        metrics = ((payload.get("tables") or {}).get("model_promotion_metric") or []) if isinstance(payload, dict) else []
        summary = evaluation.summarize_threshold_results(metrics)
    return dict(summary)


def _review_payload(summary: dict[str, Any], *, evidence_source: str, local_fallback_review: bool) -> dict[str, Any]:
    decision = "deferred"
    reasons: list[str] = []
    if evidence_source != "real_database_evaluation" and not local_fallback_review:
        reasons.append("fixture_or_local_evidence_must_defer")
    if summary.get("promotion_gate_state") != "passed":
        reasons.extend(str(item) for item in summary.get("failed_thresholds") or [])
    return {
        "review_decision": decision,
        "reason_codes": reasons or ["requires_explicit_agent_approval_before_activation"],
        "threshold_summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path)
    parser.add_argument("--model-rows", type=Path)
    parser.add_argument("--evaluation-summary-json", type=Path)
    parser.add_argument("--evidence-source", default="fixture_or_local_jsonl")
    parser.add_argument("--local-fallback-review", action="store_true")
    args = parser.parse_args(argv)
    if args.evaluation_summary_json:
        summary = _summary_from_evaluation_json(args.evaluation_summary_json)
    else:
        if not args.feature_rows:
            parser.error("--feature-rows is required unless --evaluation-summary-json is supplied")
        feature_rows = _read_rows(args.feature_rows)
        model_rows = _read_rows(args.model_rows) if args.model_rows else generator.generate_rows(feature_rows)
        artifacts = evaluation.build_evaluation_artifacts(feature_rows=feature_rows, model_rows=model_rows, evidence_source=args.evidence_source)
        summary = evaluation.summarize_threshold_results(artifacts.eval_metrics)
    print(json.dumps(_review_payload(summary, evidence_source=args.evidence_source, local_fallback_review=args.local_fallback_review), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

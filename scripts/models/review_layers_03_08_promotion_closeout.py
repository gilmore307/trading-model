#!/usr/bin/env python3
"""Agent-reviewed production-promotion closeout for Layers 3-8.

Layers 1-2 have real database evaluation paths. Layers 3-8 do not yet have
production evaluation substrate for their accepted contracts. This script builds
blocked evaluation artifacts, creates model-side promotion candidate evidence,
and calls a reviewer agent. Durable promotion decisions and activation remain in
`trading-manager`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from model_governance.promotion import build_model_config_ref, build_promotion_candidate_evidence
from model_governance.promotion.agent_review import build_review_artifact_from_review, extract_json_object, validate_promotion_review

CLOSEOUT_DATE = "2026-05-08"
CLOSEOUT_TS = "2026-05-08T00:00:00-04:00"
CONFIG_HASH = "production_closeout_no_eval_substrate_2026_05_08"

LAYER_CLOSEOUTS: tuple[dict[str, Any], ...] = (
    {
        "layer": 3,
        "model_id": "model_03_target_state_vector",
        "model_name": "TargetStateVectorModel",
        "feature_key": "feature_03_target_state_vector",
        "blocker": "no production SQL evidence table / eval run exists for current contract",
        "required_next_steps": [
            "Create production SQL evidence for feature_03_target_state_vector under point-in-time target-candidate identity rules.",
            "Generate production labels for target-context outcomes without ticker/company identity leakage.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "layer": 4,
        "model_id": "model_08_event_risk_governor",
        "model_name": "EventRiskGovernor",
        "feature_key": "source_08_event_risk_governor + event_context_vector",
        "blocker": "no production event-overlay evaluation run or calibrated labels exist",
        "required_next_steps": [
            "Create point-in-time event overlay evaluation rows with canonical event refs and dedup status.",
            "Generate calibrated post-event outcome labels by horizon.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "layer": 5,
        "model_id": "model_04_alpha_confidence",
        "model_name": "AlphaConfidenceModel",
        "feature_key": "alpha_confidence_vector",
        "blocker": "no production adjusted-alpha evaluation run or calibrated labels exist",
        "required_next_steps": [
            "Create production alpha-confidence inference rows from accepted upstream layer outputs.",
            "Generate adjusted-alpha labels and residual-return outcomes by horizon.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "layer": 6,
        "model_id": "model_05_position_projection",
        "model_name": "PositionProjectionModel",
        "feature_key": "position_projection_vector",
        "blocker": "no production position-utility evaluation run or labels exist",
        "required_next_steps": [
            "Create production position-projection inference rows with current/pending exposure and risk-budget context.",
            "Generate realized position-utility labels and baseline utility comparisons.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "layer": 7,
        "model_id": "model_06_underlying_action",
        "model_name": "UnderlyingActionModel",
        "feature_key": "underlying_action_plan",
        "blocker": "no production realized-action outcome evaluation run exists",
        "required_next_steps": [
            "Create production underlying-action plan rows from accepted upstream layer outputs.",
            "Generate realized entry/target/stop/slippage/spread outcome labels.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "layer": 8,
        "model_id": "model_07_option_expression",
        "model_name": "OptionExpressionModel",
        "feature_key": "option_expression_plan",
        "blocker": "no production option-chain replay evaluation run exists",
        "required_next_steps": [
            "Create production option-expression rows from accepted Layer 7 assumptions plus option-chain evidence.",
            "Generate option-chain replay labels, premium-risk outcomes, and expression baseline comparisons.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
)


def closeout_for_layer(layer: int) -> dict[str, Any]:
    for item in LAYER_CLOSEOUTS:
        if int(item["layer"]) == layer:
            return dict(item)
    raise ValueError(f"unsupported layer: {layer}")


def build_blocked_evaluation_artifacts(closeout: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    layer = int(closeout["layer"])
    prefix = f"l{layer:02d}"
    model_id = str(closeout["model_id"])
    feature_key = str(closeout["feature_key"])
    blocker = str(closeout["blocker"])
    request_id = f"mdreq_closeout_{prefix}_no_eval_substrate_20260508"
    snapshot_id = f"mdsnap_closeout_{prefix}_no_eval_substrate_20260508"
    eval_run_id = f"mdevrun_closeout_{prefix}_no_eval_substrate_20260508"
    metric_id = f"mpmet_closeout_{prefix}_production_eval_run_missing"
    return {
        "model_dataset_request": [
            {
                "request_id": request_id,
                "model_id": model_id,
                "purpose": "production_promotion_closeout",
                "required_data_start_time": CLOSEOUT_TS,
                "required_data_end_time": CLOSEOUT_TS,
                "required_source_key": feature_key,
                "required_feature_key": feature_key,
                "request_status": "blocked",
                "request_payload_json": {"closeout_date": CLOSEOUT_DATE, "blocker": blocker, "no_activation": True},
                "completed_at": CLOSEOUT_TS,
                "status_detail": blocker,
            }
        ],
        "model_dataset_snapshot": [
            {
                "snapshot_id": snapshot_id,
                "model_id": model_id,
                "request_id": request_id,
                "feature_schema": "missing_production_eval_substrate",
                "feature_table": feature_key,
                "data_start_time": CLOSEOUT_TS,
                "data_end_time": CLOSEOUT_TS,
                "feature_row_count": 0,
                "feature_data_hash": f"no_rows_{prefix}_20260508",
                "model_config_hash": CONFIG_HASH,
                "snapshot_payload_json": {"closeout_status": "blocked_no_production_eval_substrate", "blocker": blocker},
            }
        ],
        "model_eval_run": [
            {
                "eval_run_id": eval_run_id,
                "model_id": model_id,
                "snapshot_id": snapshot_id,
                "run_name": "production_promotion_closeout_no_eval_substrate",
                "model_version": model_id,
                "config_hash": CONFIG_HASH,
                "run_status": "blocked",
                "run_payload_json": {
                    "closeout_status": "blocked_no_production_eval_substrate",
                    "blocker": blocker,
                    "no_metrics_or_labels_available": True,
                },
                "completed_at": CLOSEOUT_TS,
                "status_detail": blocker,
            }
        ],
        "model_promotion_metric": [
            {
                "metric_id": metric_id,
                "eval_run_id": eval_run_id,
                "split_id": None,
                "label_name": "production_eval_run_available",
                "target_symbol": "",
                "horizon": "all",
                "factor_name": "promotion_closeout",
                "metric_name": "production_eval_run_available",
                "metric_value": 0.0,
                "metric_payload_json": {"passed": False, "blocker": blocker},
            }
        ],
    }


def build_summary(closeout: Mapping[str, Any], artifacts: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    eval_run = artifacts["model_eval_run"][0]
    snapshot = artifacts["model_dataset_snapshot"][0]
    metric = artifacts["model_promotion_metric"][0]
    return {
        "layer": closeout["layer"],
        "model_id": closeout["model_id"],
        "model_name": closeout["model_name"],
        "eval_run_id": eval_run["eval_run_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "evidence_source": "blocked_closeout_missing_production_eval_substrate",
        "run_status": "blocked",
        "promotion_evidence_ready": False,
        "metric_value_summary": {"production_eval_run_available": {"count": 1.0, "min": 0.0, "max": 0.0, "mean": 0.0}},
        "threshold_results": {"production_eval_run_available": {"actual": 0.0, "threshold": 1.0, "comparator": ">=", "passed": False}},
        "baseline_summary": {},
        "stability_summary": {},
        "leakage_summary": {},
        "calibration_summary": {},
        "tables": {table: len(rows) for table, rows in artifacts.items()},
        "blocking_gap": closeout["blocker"],
        "required_next_steps": list(closeout["required_next_steps"]),
        "metric_refs": [metric["metric_id"]],
        "write_policy": "model_side_review_artifact_only_manager_control_plane_required",
    }


def build_generic_promotion_prompt(*, closeout: Mapping[str, Any], evaluation_summary: Mapping[str, Any], config_version_row: Mapping[str, Any], promotion_candidate_row: Mapping[str, Any]) -> str:
    evidence = {
        "closeout": dict(closeout),
        "evaluation_summary": dict(evaluation_summary),
        "model_config_ref": dict(config_version_row),
        "promotion_candidate": dict(promotion_candidate_row),
    }
    return (
        f"You are the independent promotion reviewer for trading-model Layer {closeout['layer']} {closeout['model_name']}.\n"
        "Evaluate whether this candidate can be promoted. Be strict.\n\n"
        "Hard rules:\n"
        "- Return ONLY one JSON object. No markdown, no prose outside JSON.\n"
        "- Do not approve if production evaluation substrate is missing, if run_status is blocked, if metric_value_summary is missing or only reports production_eval_run_available=0, if labels/metrics/baselines/stability/leakage/calibration are absent, or if threshold_results fail.\n"
        "- Promotion requires a real production evaluation run, point-in-time dataset snapshot, labels, metrics, baseline comparison, split/refit stability, leakage checks, calibration evidence, and passing thresholds.\n"
        "- If evidence is insufficient, use decision_type='defer' and decision_status='deferred'.\n"
        "- A model-side review artifact is not a durable manager decision or active production pointer. Deferred/rejected reviews must not activate config.\n\n"
        "Required JSON schema:\n"
        "{\n"
        "  \"can_promote\": boolean,\n"
        "  \"decision_type\": \"approve\" | \"reject\" | \"defer\",\n"
        "  \"decision_status\": \"accepted\" | \"rejected\" | \"deferred\",\n"
        "  \"confidence\": number,\n"
        "  \"reasons\": [string],\n"
        "  \"blockers\": [string],\n"
        "  \"required_next_steps\": [string],\n"
        "  \"evidence_checks\": { string: boolean }\n"
        "}\n\n"
        "Evidence:\n"
        f"{json.dumps(evidence, indent=2, sort_keys=True, default=str)}\n"
    )


def _extract_agent_text(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        raise ValueError("openclaw agent returned empty stdout")
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(parsed, dict):
        for key in ("message", "reply", "response", "content", "text", "output"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for payload_container in (parsed, parsed.get("result")):
            if isinstance(payload_container, dict):
                payloads = payload_container.get("payloads")
                if isinstance(payloads, list):
                    for payload in payloads:
                        if isinstance(payload, dict) and isinstance(payload.get("text"), str) and payload["text"].strip():
                            return payload["text"]
        for value in parsed.values():
            if isinstance(value, dict):
                for key in ("message", "reply", "response", "content", "text"):
                    nested = value.get(key)
                    if isinstance(nested, str) and nested.strip():
                        return nested
    return stripped


def invoke_agent(*, prompt: str, openclaw_bin: str, agent: str | None, model: str | None, thinking: str, timeout_seconds: int) -> dict[str, Any]:
    command = [openclaw_bin, "agent", "--message", prompt, "--json", "--thinking", thinking, "--timeout", str(timeout_seconds)]
    if agent:
        command.extend(["--agent", agent])
    if model:
        command.extend(["--model", model])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return validate_promotion_review(extract_json_object(_extract_agent_text(result.stdout)))


def build_rows(closeout: Mapping[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    artifacts = build_blocked_evaluation_artifacts(closeout)
    summary = build_summary(closeout, artifacts)
    config_row = build_model_config_ref(
        model_id=str(closeout["model_id"]),
        model_version=str(closeout["model_id"]),
        config_hash=CONFIG_HASH,
        config_payload={"promotion_closeout": "blocked_no_production_eval_substrate", "blocker": closeout["blocker"]},
        status_detail="not eligible for production activation",
    )
    eval_run_id = artifacts["model_eval_run"][0]["eval_run_id"]
    candidate_row = build_promotion_candidate_evidence(
        model_id=str(closeout["model_id"]),
        config_ref_id=config_row["config_ref_id"],
        eval_run_id=str(eval_run_id),
        proposed_by="agent_promotion_closeout_script",
        candidate_payload={"evaluation_summary": summary},
        status_detail="agent-reviewed deferred closeout candidate; missing production evaluation substrate",
    )
    prompt = build_generic_promotion_prompt(
        closeout=closeout,
        evaluation_summary=summary,
        config_version_row=config_row,
        promotion_candidate_row=candidate_row,
    )
    return artifacts, summary, config_row, candidate_row, prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", type=int, choices=[3, 4, 5, 6, 7, 8], help="Layer to review. Omit with --all.")
    parser.add_argument("--all", action="store_true", help="Review Layers 3-8.")
    parser.add_argument("--dry-run", action="store_true", help="Print evidence/prompt without invoking agent or writing manager-control-plane SQL.")
    parser.add_argument("--openclaw-bin", default="openclaw")
    parser.add_argument("--agent", default="trader")
    parser.add_argument("--model", help="Optional model override for openclaw agent --model.")
    parser.add_argument("--thinking", default="high")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-json", type=Path, help="Optional receipt JSON path.")
    args = parser.parse_args(argv)

    if not args.all and args.layer is None:
        raise SystemExit("provide --layer or --all")
    closeouts = [closeout_for_layer(layer) for layer in range(3, 9)] if args.all else [closeout_for_layer(int(args.layer))]
    receipts: list[dict[str, Any]] = []
    for closeout in closeouts:
        artifacts, summary, config_row, candidate_row, prompt = build_rows(closeout)
        if args.dry_run:
            receipts.append({"closeout": closeout, "summary": summary, "model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_prompt": prompt})
            continue
        review = invoke_agent(
            prompt=prompt,
            openclaw_bin=args.openclaw_bin,
            agent=args.agent,
            model=args.model,
            thinking=args.thinking,
            timeout_seconds=args.timeout_seconds,
        )
        review_artifact = build_review_artifact_from_review(
            candidate_ref=candidate_row["candidate_ref"],
            review=review,
            reviewed_by="agent_promotion_reviewer",
        )
        receipts.append({"closeout": closeout, "summary": summary, "model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_review": review, "promotion_review_artifact": review_artifact})

    output = {"receipts": receipts, "manager_control_plane_required": True, "activation_attempted": False}
    rendered = json.dumps(output, indent=2, sort_keys=True, default=str)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {args.output_json}")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

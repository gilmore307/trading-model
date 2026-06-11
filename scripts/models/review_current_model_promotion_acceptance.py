#!/usr/bin/env python3
"""Codex-reviewed production-promotion acceptance for current M03-M06.

M01-M02 have real database evaluation paths. M03-M06 do not yet have production
evaluation substrate for their accepted contracts. This script builds blocked
evaluation artifacts, creates model-side promotion candidate evidence, and calls
Codex CLI for reviewer evidence. Durable promotion decisions and activation
remain in `trading-manager`.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from model_governance.promotion import build_model_config_ref, build_promotion_candidate_evidence
from model_governance.codex_cli import DEFAULT_CODEX_MODEL, invoke_codex_cli
from model_governance.promotion.agent_review import build_review_artifact_from_review, extract_json_object, validate_promotion_review

ACCEPTANCE_DATE = "2026-05-08"
ACCEPTANCE_TS = "2026-05-08T00:00:00-04:00"
CONFIG_HASH = "production_acceptance_no_eval_substrate_2026_05_08"

MODEL_ACCEPTANCES: tuple[dict[str, Any], ...] = (
    {
        "model_number": 3,
        "model_id": "event_state_model",
        "model_name": "EventStateModel",
        "feature_key": "event_state_vector",
        "blocker": "no production EventStateModel evaluation substrate exists for current contract",
        "required_next_steps": [
            "Create production EventStateModel inference rows under point-in-time event identity rules.",
            "Generate production labels for event-state outcomes without future-event leakage.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "model_number": 4,
        "model_id": "unified_decision_model",
        "model_name": "UnifiedDecisionModel",
        "feature_key": "unified_decision_vector",
        "blocker": "no production UnifiedDecisionModel evaluation substrate exists",
        "required_next_steps": [
            "Create production unified-decision rows from accepted M01-M03 context.",
            "Generate realized decision-utility labels by horizon.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "model_number": 5,
        "model_id": "option_expression_model",
        "model_name": "OptionExpressionModel",
        "feature_key": "option_expression_plan",
        "blocker": "no production option-expression replay evaluation run exists",
        "required_next_steps": [
            "Create production option-expression rows from accepted M04 decisions plus option-chain evidence.",
            "Generate option-chain replay labels, premium-risk outcomes, and expression baseline comparisons.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
    {
        "model_number": 6,
        "model_id": "residual_event_governance_model",
        "model_name": "ResidualEventGovernanceModel",
        "feature_key": "event_risk_intervention",
        "blocker": "no production residual event governance evaluation run or reviewed residual event-risk labels exist",
        "required_next_steps": [
            "Create production ResidualEventGovernanceModel inference rows from reviewed M06 data and feature evidence.",
            "Generate direction-neutral event-risk, intervention-quality, residual-warning, and event-adjusted outcome labels.",
            "Run baseline, stability, leakage, calibration, and promotion-metric evaluation before re-review.",
        ],
    },
)


def acceptance_for_model_number(model_number: int) -> dict[str, Any]:
    for item in MODEL_ACCEPTANCES:
        if int(item["model_number"]) == model_number:
            return dict(item)
    raise ValueError(f"unsupported model number: {model_number}")


def build_blocked_evaluation_artifacts(acceptance: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    model_number = int(acceptance["model_number"])
    prefix = f"m{model_number:02d}"
    model_id = str(acceptance["model_id"])
    feature_key = str(acceptance["feature_key"])
    blocker = str(acceptance["blocker"])
    request_id = f"mdreq_acceptance_{prefix}_no_eval_substrate_20260508"
    snapshot_id = f"mdsnap_acceptance_{prefix}_no_eval_substrate_20260508"
    eval_run_id = f"mdevrun_acceptance_{prefix}_no_eval_substrate_20260508"
    metric_id = f"mpmet_acceptance_{prefix}_production_eval_run_missing"
    return {
        "model_dataset_request": [
            {
                "request_id": request_id,
                "model_id": model_id,
                "purpose": "production_promotion_acceptance",
                "required_data_start_time": ACCEPTANCE_TS,
                "required_data_end_time": ACCEPTANCE_TS,
                "required_source_key": feature_key,
                "required_feature_key": feature_key,
                "request_status": "blocked",
                "request_payload_json": {"acceptance_date": ACCEPTANCE_DATE, "blocker": blocker, "no_activation": True},
                "completed_at": ACCEPTANCE_TS,
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
                "data_start_time": ACCEPTANCE_TS,
                "data_end_time": ACCEPTANCE_TS,
                "feature_row_count": 0,
                "feature_data_hash": f"no_rows_{prefix}_20260508",
                "model_config_hash": CONFIG_HASH,
                "snapshot_payload_json": {"acceptance_status": "blocked_no_production_eval_substrate", "blocker": blocker},
            }
        ],
        "model_eval_run": [
            {
                "eval_run_id": eval_run_id,
                "model_id": model_id,
                "snapshot_id": snapshot_id,
                "run_name": "production_promotion_acceptance_no_eval_substrate",
                "model_version": model_id,
                "config_hash": CONFIG_HASH,
                "run_status": "blocked",
                "run_payload_json": {
                    "acceptance_status": "blocked_no_production_eval_substrate",
                    "blocker": blocker,
                    "no_metrics_or_labels_available": True,
                },
                "completed_at": ACCEPTANCE_TS,
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
                "factor_name": "promotion_acceptance",
                "metric_name": "production_eval_run_available",
                "metric_value": 0.0,
                "metric_payload_json": {"passed": False, "blocker": blocker},
            }
        ],
    }


def build_summary(acceptance: Mapping[str, Any], artifacts: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    eval_run = artifacts["model_eval_run"][0]
    snapshot = artifacts["model_dataset_snapshot"][0]
    metric = artifacts["model_promotion_metric"][0]
    return {
        "model_number": acceptance["model_number"],
        "model_id": acceptance["model_id"],
        "model_name": acceptance["model_name"],
        "eval_run_id": eval_run["eval_run_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "evidence_source": "blocked_acceptance_missing_production_eval_substrate",
        "run_status": "blocked",
        "promotion_evidence_ready": False,
        "metric_value_summary": {"production_eval_run_available": {"count": 1.0, "min": 0.0, "max": 0.0, "mean": 0.0}},
        "threshold_results": {"production_eval_run_available": {"actual": 0.0, "threshold": 1.0, "comparator": ">=", "passed": False}},
        "baseline_summary": {},
        "stability_summary": {},
        "leakage_summary": {},
        "calibration_summary": {},
        "tables": {table: len(rows) for table, rows in artifacts.items()},
        "blocking_gap": acceptance["blocker"],
        "required_next_steps": list(acceptance["required_next_steps"]),
        "metric_refs": [metric["metric_id"]],
        "write_policy": "model_side_review_artifact_only_manager_control_plane_required",
    }


def build_generic_promotion_prompt(*, acceptance: Mapping[str, Any], evaluation_summary: Mapping[str, Any], config_version_row: Mapping[str, Any], promotion_candidate_row: Mapping[str, Any]) -> str:
    evidence = {
        "acceptance": dict(acceptance),
        "evaluation_summary": dict(evaluation_summary),
        "model_config_ref": dict(config_version_row),
        "promotion_candidate": dict(promotion_candidate_row),
    }
    return (
        f"You are the independent promotion reviewer for trading-model M{int(acceptance['model_number']):02d} {acceptance['model_name']}.\n"
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
        raise ValueError("codex cli returned empty stdout")
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


def invoke_agent(*, prompt: str, codex_bin: str, model: str | None, timeout_seconds: int) -> dict[str, Any]:
    return validate_promotion_review(extract_json_object(_extract_agent_text(invoke_codex_cli(prompt=prompt, codex_bin=codex_bin, model=model, timeout_seconds=timeout_seconds))))


def build_rows(acceptance: Mapping[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    artifacts = build_blocked_evaluation_artifacts(acceptance)
    summary = build_summary(acceptance, artifacts)
    config_row = build_model_config_ref(
        model_id=str(acceptance["model_id"]),
        model_version=str(acceptance["model_id"]),
        config_hash=CONFIG_HASH,
        config_payload={"promotion_acceptance": "blocked_no_production_eval_substrate", "blocker": acceptance["blocker"]},
        status_detail="not eligible for production activation",
    )
    eval_run_id = artifacts["model_eval_run"][0]["eval_run_id"]
    candidate_row = build_promotion_candidate_evidence(
        model_id=str(acceptance["model_id"]),
        config_ref_id=config_row["config_ref_id"],
        eval_run_id=str(eval_run_id),
        proposed_by="agent_promotion_acceptance_script",
        candidate_payload={"evaluation_summary": summary},
        status_detail="agent-reviewed deferred acceptance candidate; missing production evaluation substrate",
    )
    prompt = build_generic_promotion_prompt(
        acceptance=acceptance,
        evaluation_summary=summary,
        config_version_row=config_row,
        promotion_candidate_row=candidate_row,
    )
    return artifacts, summary, config_row, candidate_row, prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-number", type=int, choices=[3, 4, 5, 6], help="Current model number to review. Omit with --all.")
    parser.add_argument("--all", action="store_true", help="Review M03-M06.")
    parser.add_argument("--dry-run", action="store_true", help="Print evidence/prompt without invoking agent or writing manager-control-plane SQL.")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL, help="Codex model override. Defaults to gpt-5.5.")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-json", type=Path, help="Optional receipt JSON path.")
    args = parser.parse_args(argv)

    if not args.all and args.model_number is None:
        raise SystemExit("provide --model-number or --all")
    acceptances = [acceptance_for_model_number(model_number) for model_number in range(3, 7)] if args.all else [acceptance_for_model_number(int(args.model_number))]
    receipts: list[dict[str, Any]] = []
    for acceptance in acceptances:
        artifacts, summary, config_row, candidate_row, prompt = build_rows(acceptance)
        if args.dry_run:
            receipts.append({"acceptance": acceptance, "summary": summary, "model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_prompt": prompt})
            continue
        review = invoke_agent(
            prompt=prompt,
            codex_bin=args.codex_bin,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
        )
        review_artifact = build_review_artifact_from_review(
            candidate_ref=candidate_row["candidate_ref"],
            review=review,
            reviewed_by="agent_promotion_reviewer",
        )
        receipts.append({"acceptance": acceptance, "summary": summary, "model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_review": review, "promotion_review_artifact": review_artifact})

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

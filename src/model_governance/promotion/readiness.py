"""Promotion-readiness checks shared by model-layer review flows."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_PROMOTION_EVIDENCE_FIELDS = (
    "dataset_snapshot_ref",
    "dataset_split_ref",
    "eval_label_refs",
    "eval_run_ref",
    "promotion_metric_refs",
    "promotion_candidate_ref",
    "thresholds_ref",
    "baseline_comparison_ref",
    "split_stability_ref",
    "leakage_check_ref",
    "calibration_report_ref",
    "decision_record_ref",
)

LAYER_PROMOTION_READINESS_MATRIX = (
    {
        "layer": 1,
        "model_id": "background_context_model",
        "output": "background_context_state",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "real background-context dataset assembly, labels, baseline, stability, leakage, and calibration evidence missing",
    },
    {
        "layer": 2,
        "model_id": "target_state_model",
        "output": "target_context_state",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "real target-state dataset assembly, upstream M01 evidence, labels, baseline, stability, leakage, and calibration evidence missing",
    },
    {
        "layer": 3,
        "model_id": "event_state_model",
        "output": "event_state_vector",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "real event-state dataset assembly, accepted event-family inputs, labels, baseline, stability, leakage, and calibration evidence missing",
    },
    {
        "layer": 4,
        "model_id": "unified_decision_model",
        "output": "unified_decision_vector",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "unified decision training/evaluation run, direct utility labels, and replay evidence missing",
    },
    {
        "layer": 5,
        "model_id": "option_expression_model",
        "output": "option_expression_plan",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "option-chain replay labels, cost/fill/theta/IV validation, and baseline evidence missing",
    },
    {
        "layer": 6,
        "model_id": "residual_event_governance_model",
        "output": "event_risk_intervention",
        "design_status": "design_closed",
        "production_promotion_status": "deferred_deterministic_pilot_only",
        "blocking_gap": "residual event-governance evaluation run, overblock/accounting metrics, and calibrated residual-risk labels missing",
    },
)

_APPROVABLE_STATUS_VALUES = {"approved", "accepted", "production_approved"}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value) > 0
    return True


def validate_promotion_evidence_package(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return readiness decision metadata for one model promotion candidate.

    This helper intentionally does not approve models. It enforces the generic
    evidence shape required before a human/agent review may approve production
    promotion. Missing evidence means the only safe review action is defer.
    """
    missing = [field for field in REQUIRED_PROMOTION_EVIDENCE_FIELDS if not _has_value(evidence.get(field))]
    gates = evidence.get("gate_results") or {}
    failed_gates = sorted(gate for gate, passed in dict(gates).items() if passed is not True)
    requested_status = str(evidence.get("requested_decision_status") or "").strip().lower()
    ready = not missing and not failed_gates
    approval_requested = requested_status in _APPROVABLE_STATUS_VALUES
    return {
        "ready_for_promotion_review": ready,
        "approval_allowed": ready,
        "defer_required": not ready,
        "missing_evidence_fields": missing,
        "failed_gate_names": failed_gates,
        "requested_decision_status": requested_status or None,
        "approval_request_is_valid": (ready if approval_requested else None),
        "review_action": "review_may_consider_approval" if ready else "defer_promotion",
    }

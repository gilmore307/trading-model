"""ResidualEventGovernanceModel generator.

M06 consumes the current M04 unified-decision thesis, optional M05 option
expression context, and point-in-time event observations. It emits current
``6_*`` residual-event governance scores plus an ``event_risk_intervention``
policy payload. Retired Layer 10 scoring is used only as migration-source
math and is transformed before leaving this package.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping, Sequence

from models.model_10_event_risk_governor import generate_rows as _generate_legacy_event_rows

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_STEP, MODEL_VERSION


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [dict(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M06 residual event governance input row is required")
    rows.sort(key=lambda row: (str(row.get("available_time") or ""), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    legacy_row = _legacy_input_row(row)
    legacy = _generate_legacy_event_rows([legacy_row], model_version="migration_source_event_context_vector_contract")[0]
    scores = _rename_score_payload(legacy.get("event_context_vector") or {})
    dominant_by_horizon = _rename_dominant_payload(
        (legacy.get("event_risk_governor_diagnostics") or {}).get("dominant_impact_scope_by_horizon") or {}
    )
    policy = _intervention_policy(scores)
    available_time = str(legacy.get("available_time") or row.get("available_time") or "")
    target_candidate_id = str(legacy.get("target_candidate_id") or row.get("target_candidate_id") or "").strip()
    intervention_ref = _stable_id("eri", target_candidate_id, available_time, model_version)
    diagnostics = dict(legacy.get("event_risk_governor_diagnostics") or {})
    governed_context = _governed_decision_context(row)
    diagnostics.pop("underlying_thesis_context", None)

    output = {
        "available_time": available_time,
        "tradeable_time": legacy.get("tradeable_time") or row.get("tradeable_time") or available_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": row.get("background_context_state_ref") or row.get("market_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref"),
        "event_state_vector_ref": row.get("event_state_vector_ref"),
        "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
        "option_expression_plan_ref": row.get("option_expression_plan_ref"),
        "event_risk_intervention_ref": intervention_ref,
        **scores,
        **policy,
        "event_risk_intervention": {
            "governed_thesis_refs": {
                "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
                "option_expression_plan_ref": row.get("option_expression_plan_ref"),
            },
            "intervention_policy": policy,
            "residual_event_scores": scores,
            "dominant_impact_scope_by_horizon": dominant_by_horizon,
            "future_event_family_packet_eligibility": _future_packet_eligibility(policy, diagnostics),
            "governed_decision_context": governed_context,
        },
        "residual_event_governance_diagnostics": {
            **diagnostics,
            "dominant_impact_scope_by_horizon": dominant_by_horizon,
            "governed_decision_context": governed_context,
            "migration_source": "model_10_event_risk_governor_scoring",
            "no_broker_or_account_mutation": True,
        },
    }
    if not output["option_expression_plan_ref"]:
        output.pop("option_expression_plan_ref")
        output["event_risk_intervention"]["governed_thesis_refs"].pop("option_expression_plan_ref")
    _validate_no_forbidden_output(output)
    return output


def _legacy_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    if "market_context_state" not in output and row.get("background_context_state") is not None:
        output["market_context_state"] = row.get("background_context_state")
    if "event_rows" not in output:
        output["event_rows"] = (
            row.get("residual_event_observations")
            or row.get("event_observations")
            or row.get("m06_residual_event_governance_data_acquisition")
            or row.get("m10_event_risk_governor_data_acquisition")
            or row.get("events")
            or []
        )
    target_state = output.get("target_context_state")
    if isinstance(target_state, Mapping):
        output["target_context_state"] = dict(target_state)
    direct_intent = row.get("direct_underlying_intent") if isinstance(row.get("direct_underlying_intent"), Mapping) else {}
    if row.get("asset_expression_route") is None and isinstance(direct_intent, Mapping):
        output["asset_expression_route"] = direct_intent.get("asset_expression_route")
    return output


def _rename_score_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    renamed: dict[str, Any] = {}
    for key, value in payload.items():
        text = str(key)
        if text.startswith("10_event_"):
            renamed[f"6_event_{text[len('10_event_'):]}"] = value
    return renamed


def _rename_dominant_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    renamed: dict[str, Any] = {}
    for key, value in payload.items():
        text = str(key)
        if text.startswith("10_event_"):
            renamed[f"6_event_{text[len('10_event_'):]}"] = value
    return renamed


def _intervention_policy(scores: Mapping[str, Any]) -> dict[str, Any]:
    risk_by_horizon: dict[str, float] = {}
    reasons: list[str] = []
    for horizon in HORIZONS:
        suffix = horizon
        risk_by_horizon[horizon] = max(
            _float(scores.get(f"6_event_gap_risk_score_{suffix}")),
            _float(scores.get(f"6_event_reversal_risk_score_{suffix}")),
            _float(scores.get(f"6_event_liquidity_disruption_score_{suffix}")),
            _float(scores.get(f"6_event_contagion_risk_score_{suffix}")),
            _float(scores.get(f"6_event_scope_escalation_risk_score_{suffix}")),
        )
    risk_horizon = max(risk_by_horizon, key=lambda horizon: risk_by_horizon[horizon])
    severity = round(risk_by_horizon[risk_horizon], 6)
    presence = max(_float(scores.get(f"6_event_presence_score_{horizon}")) for horizon in HORIZONS)
    intensity = max(_float(scores.get(f"6_event_intensity_score_{horizon}")) for horizon in HORIZONS)
    option_impact = max(_float(scores.get(f"6_event_option_impact_score_{horizon}")) for horizon in HORIZONS)
    if presence <= 0:
        action = "no_intervention"
        reasons.append("no_visible_point_in_time_event")
    elif severity >= 0.75 or intensity >= 0.85:
        action = "block_new_entry"
        reasons.append("high_residual_event_risk")
    elif severity >= 0.55:
        action = "cap_new_exposure"
        reasons.append("moderate_residual_event_risk")
    elif severity >= 0.35 or option_impact >= 0.50:
        action = "warn"
        reasons.append("residual_event_warning")
    else:
        action = "no_intervention"
        reasons.append("residual_event_risk_below_intervention_threshold")
    if option_impact >= 0.50:
        reasons.append("option_expression_sensitive_event")
    if action in {"block_new_entry", "cap_new_exposure"} and option_impact >= 0.65:
        action = "reduce_or_flatten_review"
        reasons.append("option_sensitive_high_severity_review")
    return {
        "6_resolved_intervention_action": action,
        "6_resolved_intervention_severity_score": severity,
        "6_resolved_risk_horizon": risk_horizon,
        "6_resolved_reason_codes": sorted(set(reasons)),
    }


def _future_packet_eligibility(policy: Mapping[str, Any], diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    visible_count = int(diagnostics.get("visible_event_count") or 0)
    canonical_count = int(diagnostics.get("canonical_event_count") or 0)
    severity = _float(policy.get("6_resolved_intervention_severity_score"))
    eligible = visible_count > 0 and canonical_count > 0 and severity >= 0.35
    return {
        "eligible_for_future_event_family_packet": eligible,
        "eligibility_reason_codes": (
            ["canonical_residual_event_with_material_intervention_score"]
            if eligible
            else ["insufficient_residual_event_packet_evidence"]
        ),
    }


def _governed_decision_context(row: Mapping[str, Any]) -> dict[str, Any]:
    direct_intent = row.get("direct_underlying_intent") if isinstance(row.get("direct_underlying_intent"), Mapping) else {}
    option_plan = row.get("option_expression_plan") if isinstance(row.get("option_expression_plan"), Mapping) else {}
    return {
        "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
        "option_expression_plan_ref": row.get("option_expression_plan_ref"),
        "direct_underlying_action_type": direct_intent.get("underlying_action_type")
        or direct_intent.get("planned_underlying_action_type")
        or row.get("4_resolved_underlying_action_type"),
        "direct_underlying_action_side": direct_intent.get("action_side") or row.get("4_resolved_action_side"),
        "option_expression_type": option_plan.get("selected_expression_type") or row.get("5_resolved_expression_type"),
        "option_surface_status": option_plan.get("option_surface_status") or row.get("5_resolved_option_surface_status"),
    }


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden M06 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

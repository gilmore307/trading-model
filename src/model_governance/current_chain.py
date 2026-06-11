"""Current six-model chain runner for local fixture evidence.

This module owns the smallest executable M01->M06 route for the current model
contracts. It is intentionally local/fixture evidence only: it proves contract
handoffs, label-leakage checks, and retired-field absence without implying
production promotion or runtime activation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from model_governance.local_layer_scripts import evaluate_layer, fixture_outcome_rows
from models.model_01_background_context import MODEL_ID as M01_ID
from models.model_01_background_context import MODEL_SURFACE as M01_SURFACE
from models.model_01_background_context import generate_rows as generate_background_context
from models.model_02_target_state import MODEL_ID as M02_ID
from models.model_02_target_state import MODEL_SURFACE as M02_SURFACE
from models.model_02_target_state import generate_rows as generate_target_state
from models.model_03_event_state import MODEL_ID as M03_ID
from models.model_03_event_state import MODEL_SURFACE as M03_SURFACE
from models.model_03_event_state import generate_rows as generate_event_state
from models.model_04_unified_decision import MODEL_ID as M04_ID
from models.model_04_unified_decision import MODEL_SURFACE as M04_SURFACE
from models.model_04_unified_decision import generate_rows as generate_unified_decision
from models.model_05_option_expression import MODEL_ID as M05_ID
from models.model_05_option_expression import MODEL_SURFACE as M05_SURFACE
from models.model_05_option_expression import generate_rows as generate_option_expression
from models.model_06_residual_event_governance import MODEL_ID as M06_ID
from models.model_06_residual_event_governance import MODEL_SURFACE as M06_SURFACE
from models.model_06_residual_event_governance import generate_rows as generate_residual_event_governance

CURRENT_CHAIN_MODELS: tuple[dict[str, Any], ...] = (
    {"layer": 1, "model_surface": M01_SURFACE, "model_id": M01_ID, "module_name": "models.model_01_background_context", "label_builder_name": "build_background_context_labels"},
    {"layer": 2, "model_surface": M02_SURFACE, "model_id": M02_ID, "module_name": "models.model_02_target_state", "label_builder_name": "build_target_state_labels"},
    {"layer": 3, "model_surface": M03_SURFACE, "model_id": M03_ID, "module_name": "models.model_03_event_state", "label_builder_name": "build_event_state_labels"},
    {"layer": 4, "model_surface": M04_SURFACE, "model_id": M04_ID, "module_name": "models.model_04_unified_decision", "label_builder_name": "build_unified_decision_labels"},
    {"layer": 5, "model_surface": M05_SURFACE, "model_id": M05_ID, "module_name": "models.model_05_option_expression", "label_builder_name": "build_option_expression_labels"},
    {"layer": 6, "model_surface": M06_SURFACE, "model_id": M06_ID, "module_name": "models.model_06_residual_event_governance", "label_builder_name": "build_residual_event_governance_labels"},
)

RETIRED_CHAIN_FIELDS: frozenset[str] = frozenset(
    {
        "alpha_confidence_vector",
        "alpha_confidence_vector_ref",
        "dynamic_risk_policy_state",
        "dynamic_risk_policy_state_ref",
        "position_projection_vector",
        "position_projection_vector_ref",
        "underlying_action_vector",
        "underlying_action_plan",
        "underlying_action_plan_ref",
        "event_context_vector",
        "event_context_vector_ref",
    }
)


def run_current_chain(*, input_payload: Mapping[str, Any] | None = None, evidence_source: str = "fixture_current_chain") -> dict[str, Any]:
    """Run the current M01-M06 deterministic chain and return a receipt."""

    rows = build_current_chain_rows(input_payload)
    background = rows[M01_SURFACE][0]
    target = rows[M02_SURFACE][0]
    event = rows[M03_SURFACE][0]
    decision = rows[M04_SURFACE][0]
    option = rows[M05_SURFACE][0]
    residual = rows[M06_SURFACE][0]
    evaluations = {
        model["model_surface"]: evaluate_layer(
            module_name=model["module_name"],
            label_builder_name=model["label_builder_name"],
            model_rows=rows[model["model_surface"]],
            outcome_rows=fixture_outcome_rows(model["model_surface"], rows[model["model_surface"]]),
            layer_number=model["layer"],
            model_surface=model["model_surface"],
            model_id=model["model_id"],
            evidence_source=evidence_source,
        )
        for model in CURRENT_CHAIN_MODELS
    }
    handoff_checks = _handoff_checks(background, target, event, decision, option, residual)
    retired_violations = _retired_field_violations(rows)
    leakage_failures = [
        {
            "model_surface": surface,
            "leakage_errors": evaluation["summary"].get("leakage_errors", []),
        }
        for surface, evaluation in evaluations.items()
        if evaluation["summary"].get("leakage_errors")
    ]
    blocked_reasons = []
    if any(not check["passed"] for check in handoff_checks):
        blocked_reasons.append("handoff_check_failed")
    if retired_violations:
        blocked_reasons.append("retired_field_exposed")
    if leakage_failures:
        blocked_reasons.append("label_leakage_detected")
    receipt = {
        "contract_type": "current_model_chain_receipt",
        "evidence_source": evidence_source,
        "model_order": [model["model_surface"] for model in CURRENT_CHAIN_MODELS],
        "chain_status": "passed" if not blocked_reasons else "blocked",
        "blocking_reasons": blocked_reasons,
        "activation_allowed": False,
        "production_promotion_allowed": False,
        "row_counts": {surface: len(surface_rows) for surface, surface_rows in rows.items()},
        "handoff_checks": handoff_checks,
        "retired_field_check_passed": not retired_violations,
        "retired_field_violations": retired_violations,
        "label_leakage_check_passed": not leakage_failures,
        "label_leakage_failures": leakage_failures,
        "promotion_gate_states": {
            surface: evaluation["summary"]["promotion_gate_state"]
            for surface, evaluation in evaluations.items()
        },
        "resolved_outputs": {
            "background_context_state_ref": background["background_context_state_ref"],
            "target_context_state_ref": target["target_context_state_ref"],
            "event_state_vector_ref": event["event_state_vector_ref"],
            "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
            "option_expression_plan_ref": option.get("option_expression_plan_ref"),
            "event_risk_intervention_ref": residual["event_risk_intervention_ref"],
            "resolved_underlying_action": decision["4_resolved_underlying_action_type"],
            "resolved_option_expression": option["5_resolved_expression_type"],
            "resolved_event_intervention": residual["6_resolved_intervention_action"],
        },
    }
    return {
        "receipt": receipt,
        "evaluations": evaluations,
        "rows": rows,
    }


def build_current_chain_rows(
    input_payload: Mapping[str, Any] | None = None,
    *,
    use_fixture_defaults: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Generate current M01-M06 rows from one point-in-time input payload."""

    payload = _fixture_payload(input_payload or {}) if use_fixture_defaults else dict(input_payload or {})
    background = generate_background_context([payload["background_input"]])[0]
    target = generate_target_state([_target_input(payload, background)])[0]
    event = generate_event_state([_event_input(payload, background, target)])[0]
    decision = generate_unified_decision([_decision_input(payload, background, target, event)])[0]
    option = generate_option_expression([_option_input(payload, background, event, decision)])[0]
    residual = generate_residual_event_governance([_residual_input(payload, background, target, event, decision, option)])[0]
    return {
        M01_SURFACE: [background],
        M02_SURFACE: [target],
        M03_SURFACE: [event],
        M04_SURFACE: [decision],
        M05_SURFACE: [option],
        M06_SURFACE: [residual],
    }


def _fixture_payload(overrides: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "background_input": {
            "available_time": "2026-05-07T10:30:00-04:00",
            "market_return_10min": 0.01,
            "market_return_1h": 0.02,
            "market_return_1D": 0.03,
            "market_return_1W": 0.04,
            "market_trend_quality_score": 0.78,
            "market_volatility_pressure_score": 0.22,
            "market_liquidity_support_score": 0.86,
            "sector_relative_direction_score": 0.34,
            "sector_breadth_score": 0.72,
            "sector_dispersion_score": 0.18,
            "data_quality_score": 0.92,
            "coverage_score": 0.88,
        },
        "target_candidate_id": "anon_target_001",
        "routing_symbol": "AAPL",
        "sector_type": "technology",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "anonymous_target_feature_vector": {
            "target_return_1W": 0.62,
            "target_return_1D": 0.45,
            "target_trend_quality_score": 0.78,
            "target_volatility_pressure_score": 0.20,
            "target_transition_risk_score": 0.16,
            "target_liquidity_tradability_score": 0.88,
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
        },
        "accepted_event_contracts": [
            {
                "event_id": "evt_fixture_canonical",
                "canonical_event_id": "evt_fixture_canonical",
                "event_time": "2026-05-07T10:10:00-04:00",
                "available_time": "2026-05-07T10:12:00-04:00",
                "event_category_type": "sec_filing",
                "event_intensity_score": 0.45,
                "direction_bias_score": -0.25,
                "target_relevance_score": 0.80,
                "uncertainty_score": 0.35,
                "path_risk_score": 0.28,
            }
        ],
        "quality_calibration_state": {"data_quality_score": 0.90, "walk_forward_reliability_score": 0.82, "out_of_distribution_score": 0.08},
        "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.85, "correlation_concentration_score": 0.20},
        "account_capacity_state": {"cash_capacity_score": 0.78, "drawdown_pressure_score": 0.12},
        "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
        "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
        "cost_friction_state": {"spread_cost_estimate": 0.001, "slippage_cost_estimate": 0.001, "fee_cost_estimate": 0.0005, "turnover_cost_estimate": 0.001},
        "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
        "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50_000_000, "liquidity_score": 0.95},
        "underlying_borrow_state": {"short_borrow_status": "available"},
        "risk_budget_state": {"risk_budget_available_score": 0.95},
        "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
        "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
        "option_contract_candidates": [
            {
                "contract_ref": "AAPL_CALL_GOOD",
                "quote_snapshot_ref": "qs_call_good",
                "quote_available_time": "2026-05-07T10:30:05-04:00",
                "quote_age_seconds": 12,
                "strike": 102,
                "right": "call",
                "expiration": "2026-06-06",
                "dte": 30,
                "delta": 0.52,
                "gamma": 0.04,
                "theta": -0.08,
                "vega": 0.12,
                "iv": 0.32,
                "iv_rank": 0.45,
                "bid": 2.40,
                "ask": 2.55,
                "volume": 1200,
                "open_interest": 6500,
                "contract_multiplier": 100,
            }
        ],
        "event_observations": [
            {
                "event_id": "evt_fixture_canonical",
                "canonical_event_id": "evt_fixture_canonical",
                "dedup_status": "new_information",
                "source_priority": 1,
                "event_time": "2026-05-07T10:10:00-04:00",
                "available_time": "2026-05-07T10:12:00-04:00",
                "event_category_type": "sec_filing",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "sector_type": "technology",
                "event_intensity_score": 0.9,
                "direction_bias_score": -0.7,
                "target_relevance_score": 1.0,
                "scope_confidence_score": 0.9,
            }
        ],
    }
    return _deep_update(payload, overrides)


def _target_input(payload: Mapping[str, Any], background: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available_time": background["available_time"],
        "tradeable_time": payload["tradeable_time"],
        "target_candidate_id": payload["target_candidate_id"],
        "symbol": payload["routing_symbol"],
        "background_context_state_ref": background["background_context_state_ref"],
        "background_context_state": background["background_context_state"]["score_payload"],
        "anonymous_target_feature_vector": payload["anonymous_target_feature_vector"],
    }


def _event_input(payload: Mapping[str, Any], background: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available_time": target["available_time"],
        "tradeable_time": target["tradeable_time"],
        "target_candidate_id": target["target_candidate_id"],
        "background_context_state_ref": background["background_context_state_ref"],
        "target_context_state_ref": target["target_context_state_ref"],
        "target_context_state": target["target_context_state"]["score_payload"],
        "accepted_event_contracts": payload["accepted_event_contracts"],
    }


def _decision_input(payload: Mapping[str, Any], background: Mapping[str, Any], target: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available_time": event["available_time"],
        "tradeable_time": event["tradeable_time"],
        "target_candidate_id": target["target_candidate_id"],
        "background_context_state_ref": background["background_context_state_ref"],
        "target_context_state_ref": target["target_context_state_ref"],
        "event_state_vector_ref": event["event_state_vector_ref"],
        "background_context_state": background["background_context_state"]["score_payload"],
        "target_context_state": target["target_context_state"]["score_payload"],
        "event_state_vector": event["event_state_vector"]["score_payload"],
        "quality_calibration_state": payload["quality_calibration_state"],
        "portfolio_exposure_state": payload["portfolio_exposure_state"],
        "account_capacity_state": payload["account_capacity_state"],
        "current_underlying_position_state": payload["current_underlying_position_state"],
        "pending_underlying_order_state": payload["pending_underlying_order_state"],
        "cost_friction_state": payload["cost_friction_state"],
        "underlying_quote_state": payload["underlying_quote_state"],
        "underlying_liquidity_state": payload["underlying_liquidity_state"],
        "underlying_borrow_state": payload["underlying_borrow_state"],
        "risk_budget_state": payload["risk_budget_state"],
        "policy_gate_state": payload["policy_gate_state"],
    }


def _option_input(payload: Mapping[str, Any], background: Mapping[str, Any], event: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available_time": decision["available_time"],
        "tradeable_time": decision["tradeable_time"],
        "target_candidate_id": decision["target_candidate_id"],
        "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
        "option_chain_snapshot_ref": "chain_snapshot_fixture",
        "option_quote_available_time": "2026-05-07T10:30:05-04:00",
        "underlying_quote_snapshot_ref": "underlying_quote_fixture",
        "underlying_reference_price": payload["underlying_quote_state"]["reference_price"],
        "direct_underlying_intent": decision["direct_underlying_intent"],
        "background_context_state": background["background_context_state"]["score_payload"],
        "event_state_vector": event["event_state_vector"]["score_payload"],
        "option_expression_policy": payload["option_expression_policy"],
        "option_contract_candidates": payload["option_contract_candidates"],
    }


def _residual_input(
    payload: Mapping[str, Any],
    background: Mapping[str, Any],
    target: Mapping[str, Any],
    event: Mapping[str, Any],
    decision: Mapping[str, Any],
    option: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "available_time": decision["available_time"],
        "tradeable_time": decision["tradeable_time"],
        "target_candidate_id": decision["target_candidate_id"],
        "symbol_for_join_only": payload["routing_symbol"],
        "sector_type": payload["sector_type"],
        "background_context_state_ref": background["background_context_state_ref"],
        "target_context_state_ref": target["target_context_state_ref"],
        "event_state_vector_ref": event["event_state_vector_ref"],
        "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
        "option_expression_plan_ref": option["option_expression_plan_ref"],
        "background_context_state": background["background_context_state"]["score_payload"],
        "target_context_state": target["target_context_state"]["score_payload"],
        "event_state_vector": event["event_state_vector"]["score_payload"],
        "direct_underlying_intent": decision["direct_underlying_intent"],
        "option_expression_plan": option["option_expression_plan"],
        "event_observations": payload["event_observations"],
    }


def _handoff_checks(
    background: Mapping[str, Any],
    target: Mapping[str, Any],
    event: Mapping[str, Any],
    decision: Mapping[str, Any],
    option: Mapping[str, Any],
    residual: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check("m01_to_m02_background_ref", target.get("background_context_state_ref") == background.get("background_context_state_ref")),
        _check("m02_to_m03_target_ref", event.get("target_context_state_ref") == target.get("target_context_state_ref")),
        _check("m01_to_m04_background_ref", decision.get("background_context_state_ref") == background.get("background_context_state_ref")),
        _check("m02_to_m04_target_ref", decision.get("target_context_state_ref") == target.get("target_context_state_ref")),
        _check("m03_to_m04_event_ref", decision.get("event_state_vector_ref") == event.get("event_state_vector_ref")),
        _check("m04_to_m05_unified_decision_ref", option.get("unified_decision_vector_ref") == decision.get("unified_decision_vector_ref")),
        _check("m01_to_m06_background_ref", residual.get("background_context_state_ref") == background.get("background_context_state_ref")),
        _check("m03_to_m06_event_ref", residual.get("event_state_vector_ref") == event.get("event_state_vector_ref")),
        _check("m04_to_m06_unified_decision_ref", residual.get("unified_decision_vector_ref") == decision.get("unified_decision_vector_ref")),
        _check("m05_to_m06_option_expression_ref", residual.get("option_expression_plan_ref") == option.get("option_expression_plan_ref")),
    ]


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _retired_field_violations(value: Any, path: str = "rows") -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if str(key) in RETIRED_CHAIN_FIELDS:
                violations.append(nested_path)
            violations.extend(_retired_field_violations(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            violations.extend(_retired_field_violations(nested, f"{path}[{index}]"))
    return violations


def _deep_update(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    output = deepcopy(dict(base))
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(output.get(key), Mapping):
            output[key] = _deep_update(output[key], value)
        else:
            output[key] = deepcopy(value)
    return output

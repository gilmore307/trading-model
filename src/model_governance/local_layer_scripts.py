"""Shared local CLI helpers for deterministic Layers 4-9 scripts.

These helpers keep script wrappers thin while preserving the repo boundary:
``scripts/`` owns callable entrypoints; importable implementation remains under
``src/``. The helpers intentionally build local/fixture evaluation evidence only;
production promotion still requires the accepted governance substrate.
"""
from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

LayerBuilder = Callable[[Iterable[Mapping[str, Any]], Iterable[Mapping[str, Any]]], list[dict[str, Any]]]


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Read JSONL/NDJSON or JSON rows from a local file."""

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = (
            payload.get("rows")
            or payload.get("input_rows")
            or payload.get("model_rows")
            or payload.get("outcome_rows")
            or payload.get("labels")
            or []
        )
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a list or an object with row arrays")
    return [dict(row) for row in payload if isinstance(row, Mapping)]


def write_payload(payload: Any, path: Path | None) -> None:
    """Write payload to a path or stdout-friendly JSON when path is absent."""

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_rows(rows: list[dict[str, Any]], path: Path | None) -> None:
    """Write rows as JSONL when requested, otherwise print JSON array."""

    if path is None:
        write_payload(rows, None)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    else:
        path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate_layer(module_name: str, rows: Iterable[Mapping[str, Any]], *, model_version: str | None = None) -> list[dict[str, Any]]:
    module = import_module(module_name)
    if model_version:
        return module.generate_rows(rows, model_version=model_version)
    return module.generate_rows(rows)


def evaluate_layer(
    *,
    module_name: str,
    label_builder_name: str,
    model_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    layer_number: int,
    model_surface: str,
    model_id: str,
    evidence_source: str,
) -> dict[str, Any]:
    evaluation = import_module(f"{module_name}.evaluation")
    label_builder: LayerBuilder = getattr(evaluation, label_builder_name)
    leakage_errors: list[str] = []
    leakage_checker = getattr(evaluation, "assert_no_label_leakage", None)
    if leakage_checker is not None:
        for index, row in enumerate(model_rows):
            try:
                leakage_checker(row)
            except ValueError as exc:
                leakage_errors.append(f"row[{index}]: {exc}")
    labels = label_builder(model_rows, outcome_rows)
    summary = {
        "layer_number": layer_number,
        "model_surface": model_surface,
        "model_id": model_id,
        "evidence_source": evidence_source,
        "model_row_count": len(model_rows),
        "outcome_row_count": len(outcome_rows),
        "label_row_count": len(labels),
        "label_join_coverage_rate": round(len(labels) / len(model_rows), 6) if model_rows else 0.0,
        "leakage_check_passed": not leakage_errors,
        "leakage_errors": leakage_errors,
        "promotion_gate_state": "deferred",
        "reason_codes": _reason_codes(leakage_errors=leakage_errors, model_rows=model_rows, labels=labels, evidence_source=evidence_source),
    }
    return {"summary": summary, "labels": labels}


def conservative_review(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Return the local conservative review decision for a layer scaffold."""

    reasons = list(summary.get("reason_codes") or [])
    if not reasons:
        reasons.append("requires_explicit_production_promotion_review")
    if summary.get("promotion_gate_state") != "passed":
        decision = "defer"
        status = "deferred"
    else:
        decision = "defer"
        status = "deferred"
        reasons.append("local_script_never_activates_production_config")
    return {
        "decision_type": decision,
        "decision_status": status,
        "activation_allowed": False,
        "reason_codes": sorted(set(str(reason) for reason in reasons)),
        "reviewed_summary": dict(summary),
    }


def _reason_codes(*, leakage_errors: list[str], model_rows: list[dict[str, Any]], labels: list[dict[str, Any]], evidence_source: str) -> list[str]:
    reasons: list[str] = []
    if leakage_errors:
        reasons.append("label_leakage_detected")
    if not model_rows:
        reasons.append("no_model_rows")
    if not labels:
        reasons.append("no_offline_labels")
    if evidence_source != "production_eval_substrate":
        reasons.append("fixture_or_local_evidence_must_defer")
    reasons.append("no_production_activation_from_local_layer_script")
    return reasons


# Fixture rows are intentionally tiny. They exercise each layer's deterministic
# scaffold without pretending to be production promotion evidence.
FIXTURE_INPUT_ROWS: dict[str, list[dict[str, Any]]] = {
    "model_04_event_failure_risk": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "market_context_state_ref": "mcs_fixture",
            "sector_context_state_ref": "scs_fixture",
            "target_context_state_ref": "tcs_fixture",
            "market_context_state": {"1_state_quality_score": 0.90},
            "sector_context_state": {"2_state_quality_score": 0.88},
            "target_context_state": {"3_state_quality_score": 0.90},
            "event_strategy_failure_gate_ref": "efg_fixture",
            "event_strategy_failure_gate": {
                "agent_review_decision": "accept_layer_04_event_failure_risk_scope",
                "strategy_failure_effect_score": 0.72,
                "entry_block_pressure_score": 0.65,
                "exposure_cap_pressure_score": 0.45,
                "strategy_disable_pressure_score": 0.25,
                "path_risk_amplifier_score": 0.60,
                "evidence_quality_score": 0.86,
                "applicability_confidence_score": 0.80,
            },
            "event_failure_evidence_packet_ref": "efp_fixture",
            "event_failure_evidence_packet": {"evidence_quality_score": 0.86, "applicability_confidence_score": 0.80},
        }
    ],
    "model_09_event_risk_governor": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "symbol_for_join_only": "AAPL",
            "sector_type": "technology",
            "market_context_state_ref": "mcs_fixture",
            "sector_context_state_ref": "scs_fixture",
            "target_context_state_ref": "tcs_fixture",
            "target_context_state": {"3_target_direction_score_390min": 0.5, "3_target_direction_score_60min": 0.4},
            "source_09_event_risk_governor": [
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
    ],
    "model_05_alpha_confidence": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "market_context_state_ref": "mcs_fixture",
            "sector_context_state_ref": "scs_fixture",
            "target_context_state_ref": "tcs_fixture",
            "event_failure_risk_vector_ref": "efrv_fixture",
            "market_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85, "1_state_quality_score": 0.90},
            "sector_context_state": {"2_sector_context_support_quality_score": 0.80, "2_state_quality_score": 0.88},
            "target_context_state": {
                "3_target_direction_score_390min": 0.40,
                "3_target_trend_quality_score_390min": 0.75,
                "3_target_path_stability_score_390min": 0.80,
                "3_target_noise_score_390min": 0.20,
                "3_target_transition_risk_score_390min": 0.15,
                "3_context_direction_alignment_score_390min": 0.70,
                "3_context_support_quality_score_390min": 0.80,
                "3_tradability_score_390min": 0.85,
                "3_state_quality_score": 0.90,
                "3_beta_dependency_score_390min": 0.20,
            },
            "event_failure_risk_vector": {
                "4_event_strategy_failure_risk_score_390min": 0.45,
                "4_event_entry_block_pressure_score_390min": 0.30,
                "4_event_exposure_cap_pressure_score_390min": 0.20,
                "4_event_strategy_disable_pressure_score_390min": 0.10,
                "4_event_path_risk_amplifier_score_390min": 0.35,
                "4_event_evidence_quality_score_390min": 0.85,
                "4_event_applicability_confidence_score_390min": 0.80,
            },
            "quality_calibration_state": {"sample_support_score": 0.85, "walk_forward_reliability_score": 0.80, "model_ensemble_agreement_score": 0.85, "model_disagreement_score": 0.10, "out_of_distribution_score": 0.10, "data_quality_score": 0.90},
        }
    ],
    "model_06_position_projection": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "alpha_confidence_vector_ref": "acv_fixture",
            "current_position_state_ref": "current_fixture",
            "pending_position_state_ref": "pending_fixture",
            "alpha_confidence_vector": {"5_alpha_direction_score_390min": 0.80, "5_alpha_strength_score_390min": 0.70, "5_expected_return_score_390min": 0.06, "5_alpha_confidence_score_390min": 0.90, "5_signal_reliability_score_390min": 0.85, "5_path_quality_score_390min": 0.80, "5_reversal_risk_score_390min": 0.15, "5_drawdown_risk_score_390min": 0.20, "5_alpha_tradability_score_390min": 0.90},
            "current_position_state": {"current_position_exposure_score": 0.10},
            "pending_position_state": {"pending_exposure_size": 0.10, "pending_order_fill_probability_estimate": 0.50},
            "position_level_friction": {"spread_cost_estimate": 0.02, "slippage_cost_estimate": 0.03, "fee_cost_estimate": 0.01, "turnover_cost_estimate": 0.02, "liquidity_capacity_score": 0.90},
            "portfolio_exposure_state": {"correlation_concentration_score": 0.20, "sector_exposure_limit": 0.80},
            "risk_budget_state": {"risk_budget_available_score": 0.90, "single_name_exposure_limit": 0.80},
            "policy_gate_state": {},
        }
    ],
    "model_07_underlying_action": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "alpha_confidence_vector_ref": "acv_fixture",
            "position_projection_vector_ref": "ppv_fixture",
            "alpha_confidence_vector": {"5_alpha_confidence_score_390min": 0.90, "5_expected_return_score_390min": 0.05, "5_path_quality_score_390min": 0.85, "5_reversal_risk_score_390min": 0.10, "5_drawdown_risk_score_390min": 0.20},
            "position_projection_vector": {"6_dominant_projection_horizon": "390min", "6_target_exposure_score_390min": 0.40, "6_projection_confidence_score_390min": 0.92, "6_risk_budget_fit_score_390min": 0.95, "6_cost_to_adjust_position_score_390min": 0.08, "6_position_state_stability_score_390min": 0.90},
            "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
            "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
            "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
            "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50000000, "liquidity_score": 0.95},
            "underlying_borrow_state": {"short_borrow_status": "unavailable"},
            "risk_budget_state": {"risk_budget_fit_score": 0.95},
            "policy_gate_state": {},
        }
    ],
    "model_08_option_expression": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "underlying_action_plan_ref": "uap_fixture",
            "option_chain_snapshot_ref": "chain_snapshot_fixture",
            "option_quote_available_time": "2026-05-07T10:30:05-04:00",
            "underlying_quote_snapshot_ref": "underlying_quote_fixture",
            "underlying_reference_price": 100.25,
            "underlying_action_plan": {"planned_underlying_action_type": "increase_long", "action_side": "long", "dominant_horizon": "390min", "handoff_to_layer_8": {"underlying_path_direction": "bullish", "expected_entry_price": 100.0, "expected_target_price": 105.0, "target_price_low": 103.0, "target_price_high": 106.0, "stop_loss_price": 98.0, "thesis_invalidation_price": 97.5, "expected_holding_time_minutes": 390, "path_quality_score": 0.82, "reversal_risk_score": 0.18, "drawdown_risk_score": 0.22, "expected_favorable_move_pct": 0.05, "expected_adverse_move_pct": -0.02, "entry_price_assumption": "limit_or_pullback", "underlying_action_confidence_score": 0.78}},
            "market_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85},
            "event_context_vector": {"9_event_gap_risk_score_390min": 0.20, "9_event_uncertainty_score_390min": 0.15},
            "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
            "option_contract_candidates": [
                {"contract_ref": "AAPL_CALL_GOOD", "quote_snapshot_ref": "qs_call_good", "quote_available_time": "2026-05-07T10:30:05-04:00", "quote_age_seconds": 12, "strike": 102, "moneyness": 1.02, "contract_multiplier": 100, "exercise_style": "american", "settlement_type": "physical", "is_weekly": True, "is_monthly": False, "is_adjusted_contract": False, "last_trade_time": "2026-05-07T10:29:58-04:00", "right": "call", "expiration": "2026-05-15", "dte": 8, "delta": 0.52, "gamma": 0.04, "theta": -0.08, "vega": 0.12, "iv": 0.32, "iv_rank": 0.45, "bid": 2.40, "ask": 2.55, "bid_size": 30, "ask_size": 25, "volume": 1200, "open_interest": 6500, "intrinsic_value": 2.0, "extrinsic_value": 0.475, "breakeven_price": 104.475, "theoretical_value": 2.49}
            ],
        }
    ],
}

FIXTURE_OUTCOME_ROWS: dict[str, list[dict[str, Any]]] = {
    "model_04_event_failure_risk": [{"event_failure_risk_vector_ref": "efrv_fixture", "realized_strategy_failure_390min": True, "realized_path_risk_amplification_390min": 0.25}],
    "model_09_event_risk_governor": [{"event_context_vector_ref": "ecv_3a5b6bb6c3a72d97", "realized_symbol_move_after_event_390min": -0.04}],
    "model_05_alpha_confidence": [{"alpha_confidence_vector_ref": "acv_7d1d9b0867ac4d13", "forward_return_390min": -0.05, "idiosyncratic_residual_return_390min": -0.04, "alpha_tradable_label_390min": True}],
    "model_06_position_projection": [{"position_projection_vector_ref": "ppv_f154b03e7648d661", "realized_position_utility_390min": 0.12, "realized_risk_budget_breach_390min": False}],
    "model_07_underlying_action": [{"underlying_action_plan_ref": "uap_7c6b5381d428ea0a", "entry_price_hit": True, "realized_underlying_return": 0.04, "slippage_pct": 0.001, "spread_cost_pct": 0.001}],
    "model_08_option_expression": [{"option_expression_plan_ref": "oep_8b65e90b82a73385", "realized_option_return_390min": 0.42, "target_premium_hit_before_stop_label_390min": True}],
}


def fixture_outcome_rows(model_surface: str, model_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build tiny outcome rows from actual fixture model refs."""

    rows: list[dict[str, Any]] = []
    for row in model_rows:
        if model_surface == "model_04_event_failure_risk":
            rows.append({"event_failure_risk_vector_ref": row.get("event_failure_risk_vector_ref"), "realized_strategy_failure_390min": True, "realized_path_risk_amplification_390min": 0.25})
        elif model_surface == "model_09_event_risk_governor":
            rows.append({"event_context_vector_ref": row.get("event_context_vector_ref"), "realized_symbol_move_after_event_390min": -0.04})
        elif model_surface == "model_05_alpha_confidence":
            rows.append({"alpha_confidence_vector_ref": row.get("alpha_confidence_vector_ref"), "forward_return_390min": -0.05, "idiosyncratic_residual_return_390min": -0.04, "alpha_tradable_label_390min": True})
        elif model_surface == "model_06_position_projection":
            rows.append({"position_projection_vector_ref": row.get("position_projection_vector_ref"), "realized_position_utility_390min": 0.12, "realized_risk_budget_breach_390min": False})
        elif model_surface == "model_07_underlying_action":
            rows.append({"underlying_action_plan_ref": row.get("underlying_action_plan_ref"), "entry_price_hit": True, "realized_underlying_return": 0.04, "slippage_pct": 0.001, "spread_cost_pct": 0.001})
        elif model_surface == "model_08_option_expression":
            rows.append({"option_expression_plan_ref": row.get("option_expression_plan_ref"), "realized_option_return_390min": 0.42, "target_premium_hit_before_stop_label_390min": True})
    return rows

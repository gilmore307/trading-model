"""Shared local CLI helpers for deterministic model-layer scripts.

These helpers keep script wrappers thin while preserving the repo boundary:
``scripts/`` owns callable entrypoints; importable implementation remains under
``src/``. The helpers intentionally build local/fixture evaluation evidence only;
production promotion still requires the accepted governance substrate.
"""
from __future__ import annotations

import json
from datetime import date, datetime
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

    text = json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"
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
        path.write_text("".join(json.dumps(row, sort_keys=True, default=_json_default) + "\n" for row in rows), encoding="utf-8")
    else:
        path.write_text(json.dumps(rows, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


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
    acceptance_thresholds = _acceptance_thresholds()
    threshold_results = _threshold_results(
        acceptance_thresholds,
        model_rows=model_rows,
        outcome_rows=outcome_rows,
        labels=labels,
        leakage_errors=leakage_errors,
    )
    failed_thresholds = {
        name: result
        for name, result in threshold_results.items()
        if not bool(result.get("passed"))
    }
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
        "promotion_gate_state": "deferred" if not failed_thresholds else "blocked",
        "reason_codes": _reason_codes(leakage_errors=leakage_errors, model_rows=model_rows, labels=labels, evidence_source=evidence_source),
    }
    return {
        "summary": summary,
        "acceptance_thresholds": acceptance_thresholds,
        "threshold_results": threshold_results,
        "failed_thresholds": failed_thresholds,
        "labels": labels,
    }


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


def _acceptance_thresholds() -> dict[str, float]:
    return {
        "minimum_model_rows": 1.0,
        "minimum_outcome_rows": 1.0,
        "minimum_eval_labels": 1.0,
        "minimum_label_join_coverage_rate": 1.0,
        "maximum_leakage_error_count": 0.0,
    }


def _threshold_results(
    thresholds: Mapping[str, float],
    *,
    model_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    leakage_errors: list[str],
) -> dict[str, dict[str, Any]]:
    actuals = {
        "minimum_model_rows": float(len(model_rows)),
        "minimum_outcome_rows": float(len(outcome_rows)),
        "minimum_eval_labels": float(len(labels)),
        "minimum_label_join_coverage_rate": round(len(labels) / len(model_rows), 6) if model_rows else 0.0,
        "maximum_leakage_error_count": float(len(leakage_errors)),
    }
    results: dict[str, dict[str, Any]] = {}
    for name, threshold in thresholds.items():
        actual = actuals.get(name)
        passed = actual <= threshold if name.startswith("maximum_") else actual >= threshold
        results[name] = {"actual": actual, "threshold": threshold, "passed": passed}
    return results


# Fixture rows are intentionally tiny. They exercise each layer's deterministic
# scaffold without pretending to be production promotion evidence.
FIXTURE_INPUT_ROWS: dict[str, list[dict[str, Any]]] = {
    "model_01_background_context": [
        {
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
            "market_context_features": {"source": "fixture", "breadth_sample_count": 128},
            "sector_context_features": {"source": "fixture", "sector_sample_count": 22},
        }
    ],
    "model_02_target_state": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "symbol": "AAPL",
            "background_context_state_ref": "bcs_fixture",
            "background_context_state": {
                "1_market_risk_stress_score_1W": 0.18,
                "1_market_liquidity_support_score_1W": 0.86,
                "1_background_context_quality_score_1W": 0.82,
            },
            "anonymous_target_feature_vector": {
                "target_return_1W": 0.62,
                "target_trend_quality_score": 0.78,
                "target_volatility_pressure_score": 0.20,
                "target_transition_risk_score": 0.16,
                "target_liquidity_tradability_score": 0.88,
                "symbol": "AAPL",
            },
        }
    ],
    "model_03_event_state": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "background_context_state_ref": "bcs_fixture",
            "target_context_state_ref": "tcs_fixture",
            "target_context_state": {
                "2_target_direction_score_1W": 0.62,
                "2_target_trend_quality_score_1W": 0.78,
                "2_tradability_score_1W": 0.84,
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
        }
    ],
    "model_04_unified_decision": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "background_context_state_ref": "bcs_fixture",
            "target_context_state_ref": "tcs_fixture",
            "event_state_vector_ref": "esv_fixture",
            "background_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85},
            "target_context_state": {
                "2_target_direction_score_1W": 0.80,
                "2_target_trend_quality_score_1W": 0.76,
                "2_target_path_stability_score_1W": 0.82,
                "2_target_noise_score_1W": 0.18,
                "2_target_transition_risk_score_1W": 0.14,
                "2_context_support_quality_score_1W": 0.80,
                "2_tradability_score_1W": 0.86,
            },
            "event_state_vector": {
                "3_event_entry_block_pressure_score_1W": 0.10,
                "3_event_exposure_cap_pressure_score_1W": 0.05,
                "3_event_path_risk_score_1W": 0.12,
                "3_event_uncertainty_score_1W": 0.15,
                "3_event_applicability_confidence_score_1W": 0.50,
            },
            "quality_calibration_state": {"data_quality_score": 0.90, "walk_forward_reliability_score": 0.82, "out_of_distribution_score": 0.08},
            "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.85, "correlation_concentration_score": 0.20},
            "account_capacity_state": {"cash_capacity_score": 0.78, "drawdown_pressure_score": 0.12},
            "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
            "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
            "cost_friction_state": {"spread_cost_estimate": 0.001, "slippage_cost_estimate": 0.001, "fee_cost_estimate": 0.0005, "turnover_cost_estimate": 0.001},
            "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
            "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50000000, "liquidity_score": 0.95},
            "underlying_borrow_state": {"short_borrow_status": "available"},
            "risk_budget_state": {"risk_budget_available_score": 0.95},
            "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
        }
    ],
    "model_05_option_expression": [
        {
            "available_time": "2026-05-07T10:30:00-04:00",
            "tradeable_time": "2026-05-07T10:31:00-04:00",
            "target_candidate_id": "anon_target_001",
            "unified_decision_vector_ref": "udv_fixture",
            "option_chain_snapshot_ref": "chain_snapshot_fixture",
            "option_quote_available_time": "2026-05-07T10:30:05-04:00",
            "underlying_quote_snapshot_ref": "underlying_quote_fixture",
            "underlying_reference_price": 100.25,
            "direct_underlying_intent": {
                "underlying_action_type": "open_long",
                "action_side": "long",
                "dominant_horizon": "1W",
                "handoff_to_model_05": {
                    "underlying_path_direction": "bullish",
                    "expected_entry_price": 100.0,
                    "expected_target_price": 105.0,
                    "target_price_low": 103.0,
                    "target_price_high": 106.0,
                    "stop_loss_price": 98.0,
                    "thesis_invalidation_price": 97.5,
                    "expected_holding_time_minutes": 10080,
                    "path_quality_score": 0.82,
                    "reversal_risk_score": 0.18,
                    "drawdown_risk_score": 0.22,
                    "expected_favorable_move_pct": 0.05,
                    "expected_adverse_move_pct": -0.02,
                    "entry_price_assumption": "limit_or_pullback",
                    "underlying_action_confidence_score": 0.78,
                },
            },
            "background_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85},
            "event_state_vector": {"3_event_path_risk_score_1W": 0.20, "3_event_uncertainty_score_1W": 0.15},
            "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
            "option_contract_candidates": [
                {"contract_ref": "AAPL_CALL_GOOD", "quote_snapshot_ref": "qs_call_good", "quote_available_time": "2026-05-07T10:30:05-04:00", "quote_age_seconds": 12, "strike": 102, "moneyness": 1.02, "contract_multiplier": 100, "exercise_style": "american", "settlement_type": "physical", "is_weekly": True, "is_monthly": False, "is_adjusted_contract": False, "last_trade_time": "2026-05-07T10:29:58-04:00", "right": "call", "expiration": "2026-06-06", "dte": 30, "delta": 0.52, "gamma": 0.04, "theta": -0.08, "vega": 0.12, "iv": 0.32, "iv_rank": 0.45, "bid": 2.40, "ask": 2.55, "bid_size": 30, "ask_size": 25, "volume": 1200, "open_interest": 6500, "intrinsic_value": 2.0, "extrinsic_value": 0.475, "breakeven_price": 104.475, "theoretical_value": 2.49}
            ],
        }
    ],
}

FIXTURE_OUTCOME_ROWS: dict[str, list[dict[str, Any]]] = {
    "model_01_background_context": [{"background_context_state_ref": "bcs_fixture", "future_market_volatility_1W": 0.20, "future_market_liquidity_degradation_1W": 0.05, "future_sector_dispersion_1W": 0.18, "background_context_realized_utility_1W": 0.11}],
    "model_02_target_state": [{"target_context_state_ref": "tcs_fixture", "future_target_return_1W": 0.04, "future_target_path_stability_1W": 0.82, "future_target_liquidity_1W": 0.90, "target_state_realized_utility_1W": 0.13}],
    "model_03_event_state": [{"event_state_vector_ref": "esv_fixture", "realized_event_response_1W": -0.02, "realized_event_path_risk_1W": 0.25, "realized_event_entry_block_utility_1W": 0.03, "event_state_realized_utility_1W": 0.04}],
    "model_04_unified_decision": [{"unified_decision_vector_ref": "udv_a6cc0189ed496c7e", "realized_decision_utility": 0.12, "realized_max_drawdown": -0.03}],
    "model_05_option_expression": [{"option_expression_plan_ref": "oep_0efeeb3e99931e42", "realized_option_return_1W": 0.42, "target_premium_hit_before_stop_label_1W": True}],
}


def fixture_outcome_rows(model_surface: str, model_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build tiny outcome rows from actual fixture model refs."""

    rows: list[dict[str, Any]] = []
    for row in model_rows:
        if model_surface == "model_01_background_context":
            rows.append({"background_context_state_ref": row.get("background_context_state_ref"), "future_market_volatility_1W": 0.20, "future_market_liquidity_degradation_1W": 0.05, "future_sector_dispersion_1W": 0.18, "background_context_realized_utility_1W": 0.11})
        elif model_surface == "model_02_target_state":
            rows.append({"target_context_state_ref": row.get("target_context_state_ref"), "future_target_return_1W": 0.04, "future_target_path_stability_1W": 0.82, "future_target_liquidity_1W": 0.90, "target_state_realized_utility_1W": 0.13})
        elif model_surface == "model_03_event_state":
            rows.append({"event_state_vector_ref": row.get("event_state_vector_ref"), "realized_event_response_1W": -0.02, "realized_event_path_risk_1W": 0.25, "realized_event_entry_block_utility_1W": 0.03, "event_state_realized_utility_1W": 0.04})
        elif model_surface == "model_04_unified_decision":
            rows.append({"unified_decision_vector_ref": row.get("unified_decision_vector_ref"), "realized_decision_utility": 0.12, "realized_max_drawdown": -0.03})
        elif model_surface == "model_05_option_expression":
            rows.append({"option_expression_plan_ref": row.get("option_expression_plan_ref"), "realized_option_return_1W": 0.42, "target_premium_hit_before_stop_label_1W": True})
    return rows

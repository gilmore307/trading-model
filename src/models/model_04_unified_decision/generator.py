"""UnifiedDecisionModel generator.

M04 owns the direct-underlying decision as one current six-model contract.  The
generator consumes point-in-time background, target, event, quote/liquidity,
borrow, portfolio/risk, and exposure state, then emits one
``unified_decision_vector`` with structured edge, risk, exposure, and action
heads.  It does not expose retired serial M05-M08 vectors and never emits broker
order or option-contract fields.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import (
    ENTRY_STYLES,
    FORBIDDEN_OUTPUT_FIELDS,
    HORIZON_MINUTES,
    HORIZONS,
    MODEL_ID,
    MODEL_STEP,
    MODEL_VERSION,
    PLANNED_ACTION_TYPES,
)

ET = ZoneInfo("America/New_York")
MATERIAL_GAP_THRESHOLD = 0.025
MIN_TRADE_INTENSITY = 0.05
MIN_EDGE_CONFIDENCE = 0.35


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    """Generate deterministic M04 unified-decision rows."""

    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M04 unified decision input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    background = _payload(row, "background_context_state", "market_context_state")
    target = _payload(row, "target_context_state", "target_state_vector")
    event = _payload(row, "event_state_vector", "event_failure_risk_vector")
    quality = _payload(row, "quality_calibration_state")
    portfolio = _payload(row, "portfolio_exposure_state")
    account = _payload(row, "account_capacity_state")
    current = _payload(row, "current_underlying_position_state", "current_position_state")
    pending = _payload(row, "pending_underlying_order_state", "pending_position_state")
    friction = _payload(row, "cost_friction_state", "position_level_friction")
    quote = _payload(row, "underlying_quote_state", "quote_state")
    liquidity = _payload(row, "underlying_liquidity_state", "liquidity_state")
    borrow = _payload(row, "underlying_borrow_state", "borrow_state")
    risk = _payload(row, "risk_budget_state")
    policy = _payload(row, "policy_gate_state")
    price_location = _payload(row, "price_location_state")

    exposure = _exposure_state(current, pending)
    quote_state = _quote_state(quote, liquidity)
    hard_gate_reasons = _hard_gate_reasons(quote, liquidity, risk, policy)
    horizon_details = {
        horizon: _horizon_decision(
            horizon=horizon,
            background=background,
            target=target,
            event=event,
            quality=quality,
            portfolio=portfolio,
            account=account,
            exposure=exposure,
            friction=friction,
            quote_state=quote_state,
            borrow=borrow,
            risk=risk,
            policy=policy,
            price_location=price_location,
            hard_gate_reasons=hard_gate_reasons,
        )
        for horizon in HORIZONS
    }
    resolved_horizon = _resolve_horizon(horizon_details, policy)
    dominant = horizon_details[resolved_horizon]
    action = _resolve_action(exposure=exposure, dominant=dominant, borrow=borrow, policy=policy)
    if action["underlying_action_type"] not in PLANNED_ACTION_TYPES:
        raise ValueError(f"unsupported M04 action type: {action['underlying_action_type']}")

    vector_payload = _vector_payload(horizon_details)
    resolved_reason_codes = _reason_codes(hard_gate_reasons, dominant, action)
    resolved_payload = {
        "4_resolved_decision_horizon": resolved_horizon,
        "4_resolved_underlying_action_type": action["underlying_action_type"],
        "4_resolved_action_side": action["action_side"],
        "4_resolved_target_exposure_score": dominant["target_exposure_score"],
        "4_resolved_position_gap_score": dominant["position_gap_score"],
        "4_resolved_trade_intensity_score": dominant["trade_intensity_score"],
        "4_resolved_no_trade_probability_score": dominant["no_trade_probability_score"],
        "4_resolved_action_confidence_score": dominant["action_confidence_score"],
        "4_resolved_reason_codes": resolved_reason_codes,
    }
    vector_payload.update(resolved_payload)

    ref = _stable_id("udv", target_candidate_id, available_time, model_version)
    direct_intent = _direct_underlying_intent(
        action=action,
        dominant=dominant,
        exposure=exposure,
        quote_state=quote_state,
        resolved_horizon=resolved_horizon,
        reason_codes=resolved_reason_codes,
    )
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": row.get("background_context_state_ref") or row.get("market_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref") or row.get("target_state_vector_ref"),
        "event_state_vector_ref": row.get("event_state_vector_ref") or row.get("event_failure_risk_vector_ref"),
        "portfolio_exposure_state_ref": row.get("portfolio_exposure_state_ref"),
        "risk_budget_state_ref": row.get("risk_budget_state_ref"),
        "current_exposure_state_ref": row.get("current_exposure_state_ref") or row.get("current_position_state_ref"),
        "pending_exposure_state_ref": row.get("pending_exposure_state_ref") or row.get("pending_position_state_ref"),
        "quote_snapshot_ref": quote.get("quote_snapshot_ref"),
        "unified_decision_vector_ref": ref,
        **vector_payload,
        "unified_decision_vector": vector_payload,
        "direct_underlying_intent": direct_intent,
        "unified_decision_diagnostics": {
            "head_topology": ["edge", "risk", "exposure", "action"],
            "serial_model_outputs_exposed": False,
            "hard_gate_reason_codes": hard_gate_reasons,
            "effective_current_underlying_exposure_score": exposure["effective_current_underlying_exposure_score"],
            "pending_adjusted_underlying_exposure_score": exposure["pending_adjusted_underlying_exposure_score"],
            "horizon_decisions": horizon_details,
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _horizon_decision(
    *,
    horizon: str,
    background: Mapping[str, Any],
    target: Mapping[str, Any],
    event: Mapping[str, Any],
    quality: Mapping[str, Any],
    portfolio: Mapping[str, Any],
    account: Mapping[str, Any],
    exposure: Mapping[str, float],
    friction: Mapping[str, Any],
    quote_state: Mapping[str, Any],
    borrow: Mapping[str, Any],
    risk: Mapping[str, Any],
    policy: Mapping[str, Any],
    price_location: Mapping[str, Any],
    hard_gate_reasons: Sequence[str],
) -> dict[str, Any]:
    suffix = _suffix(horizon)
    target_direction = _signed(target, f"2_target_direction_score_{suffix}", f"3_target_direction_score_{suffix}", "target_direction_score", default=0.0)
    trend_quality = _score(target, f"2_target_trend_quality_score_{suffix}", f"3_target_trend_quality_score_{suffix}", "target_trend_quality_score", default=0.55)
    path_quality = _score(target, f"2_target_path_stability_score_{suffix}", f"3_target_path_stability_score_{suffix}", "target_path_stability_score", default=0.55)
    target_noise = _score(target, f"2_target_noise_score_{suffix}", f"3_target_noise_score_{suffix}", "target_noise_score", default=0.35)
    transition_risk = _score(target, f"2_target_transition_risk_score_{suffix}", f"3_target_transition_risk_score_{suffix}", "target_transition_risk_score", default=0.25)
    tradability = _score(target, f"2_tradability_score_{suffix}", f"3_tradability_score_{suffix}", "tradability_score", default=0.65)
    support_quality = _score(target, f"2_context_support_quality_score_{suffix}", f"3_context_support_quality_score_{suffix}", "context_support_quality_score", default=0.55)

    event_pressure = _score(event, f"3_event_entry_block_pressure_score_{suffix}", f"4_event_entry_block_pressure_score_{suffix}", "event_entry_block_pressure_score", default=0.0)
    event_cap = _score(event, f"3_event_exposure_cap_pressure_score_{suffix}", f"4_event_exposure_cap_pressure_score_{suffix}", "event_exposure_cap_pressure_score", default=0.0)
    event_disable = _score(event, f"3_event_strategy_disable_pressure_score_{suffix}", f"4_event_strategy_disable_pressure_score_{suffix}", "event_strategy_disable_pressure_score", default=0.0)
    event_path_risk = _score(event, f"3_event_path_risk_score_{suffix}", f"4_event_path_risk_amplifier_score_{suffix}", "event_path_risk_score", default=0.0)
    event_uncertainty = _score(event, f"3_event_uncertainty_score_{suffix}", f"4_event_uncertainty_score_{suffix}", "event_uncertainty_score", default=0.0)
    event_response = _signed(event, f"3_event_response_direction_score_{suffix}", f"4_event_response_direction_score_{suffix}", "event_response_direction_score", default=0.0)
    applicability = _score(event, f"3_event_applicability_confidence_score_{suffix}", f"4_event_applicability_confidence_score_{suffix}", "event_applicability_confidence_score", default=0.0)

    market_stress = _score(background, f"1_market_risk_stress_score_{suffix}", "1_market_risk_stress_score", "market_risk_stress_score", default=0.25)
    market_liquidity = _score(background, f"1_market_liquidity_support_score_{suffix}", "1_market_liquidity_support_score", "market_liquidity_support_score", default=0.70)
    data_quality = _score(quality, "data_quality_score", "sample_support_score", default=0.70)
    calibration = _score(quality, "walk_forward_reliability_score", "model_ensemble_agreement_score", default=0.65)
    ood = _score(quality, "out_of_distribution_score", "model_disagreement_score", default=0.15)

    risk_budget = _risk_budget_score(portfolio, account, risk, market_stress, event_path_risk, event_disable)
    permission = _new_exposure_permission(policy, risk_budget, event_pressure, event_disable, hard_gate_reasons)
    cost_drag = _cost_drag(friction, quote_state)
    edge_direction = _clip_signed(target_direction * (1.0 - 0.30 * applicability * event_uncertainty) + 0.20 * applicability * event_response)
    edge_strength = _clip01(
        0.30 * abs(edge_direction)
        + 0.18 * trend_quality
        + 0.16 * path_quality
        + 0.14 * support_quality
        + 0.12 * tradability
        + 0.10 * (1.0 - target_noise)
    )
    downside = _clip01(0.26 * transition_risk + 0.24 * event_path_risk + 0.18 * event_pressure + 0.14 * market_stress + 0.10 * ood + 0.08 * (1.0 - market_liquidity))
    confidence = _clip01(0.30 * data_quality + 0.25 * calibration + 0.20 * path_quality + 0.15 * support_quality + 0.10 * (1.0 - ood))
    expected_return = _clip_signed(edge_direction * edge_strength * risk_budget * (1.0 - 0.55 * downside) * (1.0 - cost_drag) * 0.12)
    after_cost_edge = _clip01(0.5 + expected_return * 5.0)
    price_multiplier = _price_location_multiplier(edge_direction, price_location)
    target_exposure = _clip_signed(edge_direction * edge_strength * confidence * risk_budget * permission * (1.0 - 0.60 * downside) * (1.0 - 0.60 * event_cap) * price_multiplier)
    position_gap = _clip_signed(target_exposure - exposure["effective_current_underlying_exposure_score"])
    trade_intensity = _clip01(abs(position_gap) * (0.55 + 0.45 * confidence) * (1.0 - cost_drag))
    no_trade_probability = _clip01(
        0.45 * (1.0 - permission)
        + 0.20 * (1.0 - confidence)
        + 0.20 * (1.0 if abs(position_gap) < MATERIAL_GAP_THRESHOLD else 0.0)
        + 0.15 * (1.0 if hard_gate_reasons else downside)
    )
    action_eligibility = _clip01((1.0 - no_trade_probability) * permission * (1.0 if abs(edge_direction) >= 0.02 else 0.4))
    entry_quality = _clip01(0.35 * quote_state["liquidity_score"] + 0.25 * (1.0 - cost_drag) + 0.20 * confidence + 0.20 * (1.0 - downside))
    action_confidence = _clip01(0.35 * confidence + 0.25 * action_eligibility + 0.20 * entry_quality + 0.20 * edge_strength)
    reasons = []
    if hard_gate_reasons:
        reasons.extend(hard_gate_reasons)
    if event_pressure >= 0.60:
        reasons.append("event_entry_pressure")
    if event_cap >= 0.60:
        reasons.append("event_exposure_cap_pressure")
    if after_cost_edge <= 0.52 and after_cost_edge >= 0.48:
        reasons.append("after_cost_edge_neutral")
    if abs(position_gap) < MATERIAL_GAP_THRESHOLD:
        reasons.append("position_gap_below_materiality")
    if not reasons:
        reasons.append("unified_decision_edge_risk_exposure_action_aligned")
    return {
        "edge_direction_score": round(edge_direction, 6),
        "after_cost_edge_score": round(after_cost_edge, 6),
        "expected_return_score": round(expected_return, 6),
        "edge_confidence_score": round(confidence, 6),
        "downside_risk_score": round(downside, 6),
        "risk_budget_score": round(risk_budget, 6),
        "new_exposure_permission_score": round(permission, 6),
        "target_exposure_score": round(target_exposure, 6),
        "position_gap_score": round(position_gap, 6),
        "trade_intensity_score": round(trade_intensity, 6),
        "no_trade_probability_score": round(no_trade_probability, 6),
        "action_eligibility_score": round(action_eligibility, 6),
        "action_direction_score": round(_clip_signed(position_gap), 6),
        "entry_quality_score": round(entry_quality, 6),
        "action_confidence_score": round(action_confidence, 6),
        "cost_drag_score": round(cost_drag, 6),
        "reason_codes": sorted(set(reasons)),
    }


def _vector_payload(horizon_details: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for horizon, detail in horizon_details.items():
        suffix = _suffix(horizon)
        payload.update(
            {
                f"4_edge_direction_score_{suffix}": detail["edge_direction_score"],
                f"4_after_cost_edge_score_{suffix}": detail["after_cost_edge_score"],
                f"4_expected_return_score_{suffix}": detail["expected_return_score"],
                f"4_edge_confidence_score_{suffix}": detail["edge_confidence_score"],
                f"4_downside_risk_score_{suffix}": detail["downside_risk_score"],
                f"4_risk_budget_score_{suffix}": detail["risk_budget_score"],
                f"4_new_exposure_permission_score_{suffix}": detail["new_exposure_permission_score"],
                f"4_target_exposure_score_{suffix}": detail["target_exposure_score"],
                f"4_position_gap_score_{suffix}": detail["position_gap_score"],
                f"4_trade_intensity_score_{suffix}": detail["trade_intensity_score"],
                f"4_no_trade_probability_score_{suffix}": detail["no_trade_probability_score"],
                f"4_action_eligibility_score_{suffix}": detail["action_eligibility_score"],
                f"4_action_direction_score_{suffix}": detail["action_direction_score"],
                f"4_entry_quality_score_{suffix}": detail["entry_quality_score"],
                f"4_action_confidence_score_{suffix}": detail["action_confidence_score"],
            }
        )
    return payload


def _resolve_horizon(details: Mapping[str, Mapping[str, Any]], policy: Mapping[str, Any]) -> str:
    requested = str(policy.get("preferred_decision_horizon") or "").strip()
    if requested in details:
        return requested
    ranked = sorted(
        details.items(),
        key=lambda item: (
            float(item[1]["action_confidence_score"])
            + 0.35 * float(item[1]["trade_intensity_score"])
            - 0.25 * float(item[1]["no_trade_probability_score"])
        ),
        reverse=True,
    )
    return ranked[0][0]


def _resolve_action(*, exposure: Mapping[str, float], dominant: Mapping[str, Any], borrow: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, str]:
    current = exposure["effective_current_underlying_exposure_score"]
    target = float(dominant["target_exposure_score"])
    gap = float(dominant["position_gap_score"])
    intensity = float(dominant["trade_intensity_score"])
    no_trade_probability = float(dominant["no_trade_probability_score"])
    if no_trade_probability >= 0.70 or intensity < _minimum_trade_intensity(policy):
        action_type = "maintain" if abs(current) >= MATERIAL_GAP_THRESHOLD else "no_trade"
        return {"underlying_action_type": action_type, "action_side": _side(current)}
    if gap > 0.0:
        if current < -MATERIAL_GAP_THRESHOLD:
            return {"underlying_action_type": "cover_short", "action_side": "long"}
        return {"underlying_action_type": "increase_long" if current > MATERIAL_GAP_THRESHOLD else "open_long", "action_side": "long"}
    if current > MATERIAL_GAP_THRESHOLD and target <= 0.0:
        return {"underlying_action_type": "close_long", "action_side": "none"}
    if current > target and current > MATERIAL_GAP_THRESHOLD:
        return {"underlying_action_type": "reduce_long", "action_side": "long"}
    if gap < 0.0:
        if not _short_allowed(borrow, policy):
            action_type = "bearish_underlying_path_but_no_short_allowed" if current <= MATERIAL_GAP_THRESHOLD else "reduce_long"
            return {"underlying_action_type": action_type, "action_side": "none" if action_type.startswith("bearish") else "long"}
        return {"underlying_action_type": "increase_short" if current < -MATERIAL_GAP_THRESHOLD else "open_short", "action_side": "short"}
    return {"underlying_action_type": "maintain", "action_side": _side(current)}


def _direct_underlying_intent(
    *,
    action: Mapping[str, str],
    dominant: Mapping[str, Any],
    exposure: Mapping[str, float],
    quote_state: Mapping[str, Any],
    resolved_horizon: str,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    action_type = action["underlying_action_type"]
    action_side = action["action_side"]
    reference_price = quote_state["reference_price"]
    expected_return = float(dominant["expected_return_score"])
    adverse_move = max(0.004, float(dominant["downside_risk_score"]) * 0.05)
    favorable_move = max(0.004, abs(expected_return))
    direction = "bullish" if action_side == "long" else "bearish" if action_side == "short" else "neutral"
    entry_style = _entry_style(action_type, dominant)
    target_price = _price(reference_price, favorable_move if direction != "bearish" else -favorable_move)
    stop_price = _price(reference_price, -adverse_move if direction != "bearish" else adverse_move)
    return {
        "underlying_action_type": action_type,
        "action_side": action_side,
        "dominant_horizon": resolved_horizon,
        "target_exposure_score": dominant["target_exposure_score"],
        "current_effective_exposure_score": exposure["effective_current_underlying_exposure_score"],
        "exposure_gap_score": dominant["position_gap_score"],
        "trade_intensity_score": dominant["trade_intensity_score"],
        "no_trade_probability_score": dominant["no_trade_probability_score"],
        "entry_style": entry_style,
        "reference_price": reference_price,
        "expected_target_price": target_price,
        "thesis_invalidation_price": stop_price,
        "expected_holding_time_minutes": HORIZON_MINUTES[resolved_horizon],
        "handoff_to_model_05": {
            "underlying_path_direction": direction,
            "expected_entry_price": reference_price,
            "expected_target_price": target_price,
            "stop_loss_price": stop_price,
            "thesis_invalidation_price": stop_price,
            "expected_holding_time_minutes": HORIZON_MINUTES[resolved_horizon],
            "path_quality_score": round(1.0 - float(dominant["downside_risk_score"]), 6),
            "expected_favorable_move_pct": round(favorable_move, 6),
            "expected_adverse_move_pct": round(-adverse_move, 6),
            "entry_price_assumption": entry_style,
            "underlying_action_confidence_score": dominant["action_confidence_score"],
        },
        "reason_codes": list(reason_codes),
    }


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in (
        "background_context_state",
        "market_context_state",
        "target_context_state",
        "target_state_vector",
        "event_state_vector",
        "event_failure_risk_vector",
        "quality_calibration_state",
        "portfolio_exposure_state",
        "account_capacity_state",
        "current_underlying_position_state",
        "current_position_state",
        "pending_underlying_order_state",
        "pending_position_state",
        "cost_friction_state",
        "position_level_friction",
        "underlying_quote_state",
        "quote_state",
        "underlying_liquidity_state",
        "liquidity_state",
        "underlying_borrow_state",
        "borrow_state",
        "risk_budget_state",
        "policy_gate_state",
        "price_location_state",
    ):
        output[key] = _coerce_payload(output.get(key))
    return output


def _payload(row: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = _coerce_payload(row.get(key))
        if isinstance(value, Mapping) and value:
            return dict(value)
    return {}


def _coerce_payload(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    return value or {}


def _exposure_state(current: Mapping[str, Any], pending: Mapping[str, Any]) -> dict[str, float]:
    current_exposure = _signed(current, "current_underlying_exposure_score", "current_position_exposure_score", "current_exposure_score", default=0.0)
    pending_exposure = _signed(pending, "pending_underlying_exposure_score", "pending_exposure_size", "pending_exposure_score", default=0.0)
    fill_probability = _score(pending, "pending_fill_probability_estimate", "pending_order_fill_probability_estimate", "fill_probability_estimate", default=0.0)
    pending_adjusted = pending_exposure * fill_probability
    effective_current = _clip_signed(current_exposure + pending_adjusted)
    return {
        "current_underlying_exposure_score": round(current_exposure, 6),
        "pending_underlying_exposure_score": round(pending_exposure, 6),
        "pending_fill_probability_estimate": round(fill_probability, 6),
        "pending_adjusted_underlying_exposure_score": round(pending_adjusted, 6),
        "effective_current_underlying_exposure_score": round(effective_current, 6),
    }


def _quote_state(quote: Mapping[str, Any], liquidity: Mapping[str, Any]) -> dict[str, float]:
    reference = _first_float(quote, "reference_price", "last_price", "close_price", "bar_close")
    if reference is None:
        reference = 100.0
    spread_bps = _first_float(liquidity, "spread_bps", "effective_spread_bps")
    if spread_bps is None:
        bid = _first_float(quote, "bid_price", "bid")
        ask = _first_float(quote, "ask_price", "ask")
        spread_bps = 10000.0 * max(0.0, (ask or reference) - (bid or reference)) / max(reference, 0.0001)
    liquidity_score = _score(liquidity, "liquidity_score", "liquidity_capacity_score", default=max(0.0, 1.0 - spread_bps / 200.0))
    return {"reference_price": round(reference, 6), "spread_bps": round(spread_bps, 6), "liquidity_score": round(liquidity_score, 6)}


def _hard_gate_reasons(quote: Mapping[str, Any], liquidity: Mapping[str, Any], risk: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    halt_status = str(quote.get("halt_status") or "active").lower()
    if halt_status not in {"", "active", "normal", "open"}:
        reasons.append("halt_status_not_active")
    if str(policy.get("allow_new_exposure") or "").lower() == "false":
        reasons.append("policy_blocks_new_exposure")
    if str(policy.get("direct_underlying_action_allowed") or "true").lower() == "false":
        reasons.append("direct_underlying_action_not_allowed")
    if str(risk.get("kill_switch_state") or "").lower() == "active":
        reasons.append("risk_kill_switch_active")
    if _score(liquidity, "liquidity_score", default=1.0) <= 0.05:
        reasons.append("liquidity_unavailable")
    return sorted(set(reasons))


def _risk_budget_score(portfolio: Mapping[str, Any], account: Mapping[str, Any], risk: Mapping[str, Any], market_stress: float, event_path_risk: float, event_disable: float) -> float:
    gross_capacity = _score(portfolio, "gross_exposure_capacity_score", default=0.70)
    concentration = _score(portfolio, "correlation_concentration_score", "concentration_score", default=0.25)
    cash = _score(account, "cash_capacity_score", "premium_capacity_score", default=0.70)
    drawdown = _score(account, "drawdown_pressure_score", default=0.15)
    explicit_budget = _score(risk, "risk_budget_available_score", "risk_budget_fit_score", default=0.75)
    capacity = _clip01(0.35 * gross_capacity + 0.25 * (1.0 - concentration) + 0.20 * cash + 0.20 * (1.0 - drawdown))
    return _clip01(explicit_budget * capacity * (1.0 - 0.45 * market_stress) * (1.0 - 0.35 * event_path_risk) * (1.0 - 0.65 * event_disable))


def _new_exposure_permission(policy: Mapping[str, Any], risk_budget: float, event_pressure: float, event_disable: float, hard_gate_reasons: Sequence[str]) -> float:
    if hard_gate_reasons:
        return 0.0
    policy_floor = _score(policy, "new_exposure_permission_score", default=1.0)
    return _clip01(policy_floor * risk_budget * (1.0 - 0.45 * event_pressure) * (1.0 - 0.80 * event_disable))


def _cost_drag(friction: Mapping[str, Any], quote_state: Mapping[str, Any]) -> float:
    spread = _score(friction, "spread_cost_estimate", default=quote_state["spread_bps"] / 10000.0)
    slippage = _score(friction, "slippage_cost_estimate", default=0.001)
    fees = _score(friction, "fee_cost_estimate", default=0.0005)
    turnover = _score(friction, "turnover_cost_estimate", default=0.001)
    return _clip01(spread + slippage + fees + turnover)


def _price_location_multiplier(direction: float, price_location: Mapping[str, Any]) -> float:
    thesis_intact = _score(price_location, "thesis_intact_score", default=1.0)
    revision = _signed(price_location, "alpha_revision_score", default=0.0)
    move = _signed(price_location, "price_move_since_alpha_score", default=0.0)
    if abs(direction) < 0.001:
        return 1.0
    favorable_extension = direction * move
    if favorable_extension > 0.0 and revision <= 0.0:
        return _clip01(1.0 - 0.35 * favorable_extension)
    if favorable_extension < 0.0 and thesis_intact >= 0.75:
        return _clip01(1.0 + 0.25 * abs(favorable_extension))
    return _clip01(1.0 + 0.20 * revision)


def _entry_style(action_type: str, dominant: Mapping[str, Any]) -> str:
    if action_type in {"no_trade", "maintain"}:
        return "no_entry" if action_type == "no_trade" else "maintain_existing_entry"
    if float(dominant["entry_quality_score"]) >= 0.75:
        return "limit_near_mid"
    if float(dominant["downside_risk_score"]) >= 0.55:
        return "wait_for_pullback"
    if float(dominant["edge_confidence_score"]) >= MIN_EDGE_CONFIDENCE:
        return "limit_or_pullback"
    return "wait_for_breakout_confirmation"


def _reason_codes(hard_gate_reasons: Sequence[str], dominant: Mapping[str, Any], action: Mapping[str, str]) -> list[str]:
    reasons = [*hard_gate_reasons, *[str(reason) for reason in dominant["reason_codes"]]]
    reasons.append(f"resolved_{action['underlying_action_type']}")
    return sorted(set(reasons))


def _minimum_trade_intensity(policy: Mapping[str, Any]) -> float:
    return _clip01(_score(policy, "minimum_trade_intensity", default=MIN_TRADE_INTENSITY))


def _short_allowed(borrow: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    if str(policy.get("shorting_allowed") or "").lower() == "false":
        return False
    status = str(borrow.get("short_borrow_status") or "unavailable").lower()
    return status in {"available", "easy", "located"}


def _side(exposure: float) -> str:
    if exposure > MATERIAL_GAP_THRESHOLD:
        return "long"
    if exposure < -MATERIAL_GAP_THRESHOLD:
        return "short"
    return "none"


def _price(reference: float, move_pct: float) -> float:
    return round(max(0.0001, reference * (1.0 + move_pct)), 6)


def _score(mapping: Mapping[str, Any], *keys: str, default: float) -> float:
    value = _first_float(mapping, *keys)
    return _clip01(default if value is None else value)


def _signed(mapping: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    value = _first_float(mapping, *keys)
    return _clip_signed(default if value is None else value)


def _first_float(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return number
    return None


def _suffix(horizon: str) -> str:
    return horizon.replace(" ", "_")


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("time") or row.get("timestamp"))


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clip_signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden M04 output field {path}.{key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")


for _style in ENTRY_STYLES:
    if _style == "":
        raise RuntimeError("empty M04 entry style")

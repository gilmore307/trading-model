"""Deterministic UnderlyingActionModel V1 scaffold.

Consumes point-in-time Layer 5/6 vectors plus current/pending direct-underlying
state, quote/liquidity/borrow state, and risk/policy gates. Emits an offline
``underlying_action_plan`` and ``underlying_action_vector``. The scaffold is
intentionally conservative: it plans direct stock/ETF action only, uses pending
exposure when calculating effective exposure, blocks broker/order fields, and
never selects option contracts.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import (
    FORBIDDEN_OUTPUT_FIELDS,
    HORIZON_MINUTES,
    HORIZONS,
    MODEL_ID,
    MODEL_LAYER,
    MODEL_VERSION,
    PLANNED_ACTION_TYPES,
)

ET = ZoneInfo("America/New_York")
MATERIAL_GAP_THRESHOLD = 0.025
MIN_TRADE_INTENSITY = 0.05
DEFAULT_TARGET_RETURN_BY_HORIZON = {
    "5min": 0.006,
    "15min": 0.010,
    "60min": 0.018,
    "390min": 0.035,
}
DEFAULT_ADVERSE_MOVE_BY_HORIZON = {
    "5min": 0.004,
    "15min": 0.007,
    "60min": 0.012,
    "390min": 0.020,
}


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    """Generate deterministic Layer 7 action-plan rows.

    Each input row may provide nested dictionaries or JSON strings for:
    ``alpha_confidence_vector``, ``position_projection_vector``,
    ``current_underlying_position_state``, ``pending_underlying_order_state``,
    ``underlying_quote_state``, ``underlying_liquidity_state``,
    ``underlying_borrow_state``, ``risk_budget_state``, and ``policy_gate_state``.
    """

    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 7 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    outputs = [_model_row(row, model_version=model_version) for row in rows]
    return outputs


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    alpha = _payload(row, "alpha_confidence_vector")
    projection = _payload(row, "position_projection_vector")
    current = _payload(row, "current_underlying_position_state")
    pending = _payload(row, "pending_underlying_order_state")
    quote = _payload(row, "underlying_quote_state")
    liquidity = _payload(row, "underlying_liquidity_state")
    borrow = _payload(row, "underlying_borrow_state")
    risk = _payload(row, "risk_budget_state")
    policy = _payload(row, "policy_gate_state")

    exposure = _exposure_state(current, pending, projection)
    quote_state = _quote_state(quote, liquidity)
    gate_state = _gate_state(quote, liquidity, borrow, risk, policy, exposure)
    horizon_payloads = {
        horizon: _horizon_payload(horizon, alpha, projection, exposure, quote_state, gate_state, borrow, risk, policy)
        for horizon in HORIZONS
    }
    dominant_horizon = _dominant_horizon(horizon_payloads, projection)
    dominant = horizon_payloads[dominant_horizon]
    action = _resolve_action(exposure, dominant, gate_state, borrow, policy)
    if action["planned_underlying_action_type"] not in PLANNED_ACTION_TYPES:
        raise ValueError(f"unsupported planned action type: {action['planned_underlying_action_type']}")

    entry_plan = _entry_plan(action, dominant, quote_state, available_time)
    price_path = _price_path(action, dominant, quote_state)
    risk_plan = _risk_plan(action, dominant, quote_state, price_path)
    exposure_plan = _exposure_plan(exposure, dominant, action, quote_state)
    handoff = _layer8_handoff(entry_plan, price_path, risk_plan, dominant)
    reason_codes = _reason_codes(gate_state, dominant, action)
    action_plan_ref = _stable_id("uap", target_candidate_id, available_time, model_version)

    score_payload: dict[str, Any] = {}
    for horizon, payload in horizon_payloads.items():
        suffix = _suffix(horizon)
        score_payload.update(
            {
                f"7_underlying_trade_eligibility_score_{suffix}": payload["trade_eligibility_score"],
                f"7_underlying_action_direction_score_{suffix}": payload["action_direction_score"],
                f"7_underlying_trade_intensity_score_{suffix}": payload["trade_intensity_score"],
                f"7_underlying_entry_quality_score_{suffix}": payload["entry_quality_score"],
                f"7_underlying_expected_return_score_{suffix}": payload["expected_return_score"],
                f"7_underlying_adverse_risk_score_{suffix}": payload["adverse_risk_score"],
                f"7_underlying_reward_risk_score_{suffix}": payload["reward_risk_score"],
                f"7_underlying_liquidity_fit_score_{suffix}": payload["liquidity_fit_score"],
                f"7_underlying_holding_time_fit_score_{suffix}": payload["holding_time_fit_score"],
                f"7_underlying_action_confidence_score_{suffix}": payload["action_confidence_score"],
            }
        )

    resolved_payload = {
        "7_resolved_underlying_action_type": action["planned_underlying_action_type"],
        "7_resolved_action_side": action["action_side"],
        "7_resolved_dominant_horizon": dominant_horizon,
        "7_resolved_trade_eligibility_score": dominant["trade_eligibility_score"],
        "7_resolved_trade_intensity_score": dominant["trade_intensity_score"],
        "7_resolved_entry_quality_score": dominant["entry_quality_score"],
        "7_resolved_action_confidence_score": dominant["action_confidence_score"],
        "7_resolved_reason_codes": reason_codes,
    }

    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "alpha_confidence_vector_ref": row.get("alpha_confidence_vector_ref"),
        "position_projection_vector_ref": row.get("position_projection_vector_ref"),
        "underlying_action_plan_ref": action_plan_ref,
        **score_payload,
        **resolved_payload,
        "underlying_action_vector": {**score_payload, **resolved_payload},
        "underlying_action_plan": {
            "planned_underlying_action_type": action["planned_underlying_action_type"],
            "action_side": action["action_side"],
            "dominant_horizon": dominant_horizon,
            "trade_eligibility_score": dominant["trade_eligibility_score"],
            "action_intensity_score": dominant["trade_intensity_score"],
            "entry_quality_score": dominant["entry_quality_score"],
            "action_confidence_score": dominant["action_confidence_score"],
            "exposure_plan": exposure_plan,
            "entry_plan": entry_plan,
            "price_path_expectation": price_path,
            "risk_plan": risk_plan,
            "handoff_to_layer_8": handoff,
            "reason_codes": reason_codes,
            "diagnostics": {
                "hard_gate_reason_codes": gate_state["hard_gate_reason_codes"],
                "soft_gate_reason_codes": dominant["soft_gate_reason_codes"],
                "effective_current_underlying_exposure_score": exposure["effective_current_underlying_exposure_score"],
                "pending_adjusted_underlying_exposure_score": exposure["pending_adjusted_underlying_exposure_score"],
                "underlying_exposure_gap_score": exposure["underlying_exposure_gap_score"],
                "horizon_scores": horizon_payloads,
            },
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in (
        "alpha_confidence_vector",
        "position_projection_vector",
        "current_underlying_position_state",
        "pending_underlying_order_state",
        "underlying_quote_state",
        "underlying_liquidity_state",
        "underlying_borrow_state",
        "risk_budget_state",
        "policy_gate_state",
    ):
        output[key] = _coerce_payload(output.get(key))
    return output


def _payload(row: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = _coerce_payload(row.get(key))
    return value if isinstance(value, Mapping) else {}


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


def _exposure_state(current: Mapping[str, Any], pending: Mapping[str, Any], projection: Mapping[str, Any]) -> dict[str, float]:
    current_exposure = _first_float(
        current,
        "current_underlying_exposure_score",
        "underlying_exposure_score",
        "exposure_score",
        "current_exposure_score",
    ) or 0.0
    pending_exposure = _first_float(
        pending,
        "pending_underlying_exposure_score",
        "pending_exposure_score",
        "underlying_exposure_score",
        "exposure_score",
    ) or 0.0
    fill_probability = _first_float(
        pending,
        "pending_fill_probability_estimate",
        "fill_probability_estimate",
        "fill_probability",
    )
    if fill_probability is None:
        fill_probability = 0.0
    pending_adjusted = pending_exposure * _clip01(fill_probability)
    effective_current = current_exposure + pending_adjusted
    target_exposure = _resolved_target_exposure(projection)
    gap = target_exposure - effective_current
    return {
        "current_underlying_exposure_score": _clip_signed(current_exposure),
        "pending_underlying_exposure_score": _clip_signed(pending_exposure),
        "pending_fill_probability_estimate": _clip01(fill_probability),
        "pending_adjusted_underlying_exposure_score": _clip_signed(pending_adjusted),
        "effective_current_underlying_exposure_score": _clip_signed(effective_current),
        "target_underlying_exposure_score": _clip_signed(target_exposure),
        "underlying_exposure_gap_score": _clip_signed(gap),
    }


def _resolved_target_exposure(projection: Mapping[str, Any]) -> float:
    resolved = _first_float(projection, "6_resolved_target_exposure_score", "target_underlying_exposure_score", "target_exposure_score")
    if resolved is not None:
        return _clip_signed(resolved)
    values = [_safe_float(projection.get(f"6_target_exposure_score_{_suffix(horizon)}")) for horizon in HORIZONS]
    clean = [value for value in values if value is not None]
    if not clean:
        return 0.0
    return _clip_signed(clean[-1] if values[-1] is not None else sum(clean) / len(clean))


def _quote_state(quote: Mapping[str, Any], liquidity: Mapping[str, Any]) -> dict[str, Any]:
    bid = _first_float(quote, "bid_price", "bid")
    ask = _first_float(quote, "ask_price", "ask")
    mid = _first_float(quote, "mid_price", "mid")
    reference = _first_float(quote, "reference_price", "last_price", "close_price", "price")
    if mid is None and bid is not None and ask is not None and ask > 0:
        mid = (bid + ask) / 2.0
    if reference is None:
        reference = mid or bid or ask or 1.0
    spread_bps = _first_float(liquidity, "spread_bps")
    if spread_bps is None and bid is not None and ask is not None and mid and mid > 0:
        spread_bps = max((ask - bid) / mid * 10_000.0, 0.0)
    dollar_volume = _first_float(liquidity, "dollar_volume", "avg_dollar_volume")
    liquidity_score = _first_float(liquidity, "liquidity_fit_score", "liquidity_score")
    if liquidity_score is None:
        spread_score = None if spread_bps is None else _clip01(1.0 - min(spread_bps / 80.0, 1.0))
        volume_score = None if dollar_volume is None else _clip01(math.log10(max(dollar_volume, 1.0)) / 8.0)
        liquidity_score = _average([spread_score, volume_score])
    return {
        "bid_price": bid,
        "ask_price": ask,
        "mid_price": mid,
        "reference_price": reference,
        "spread_bps": spread_bps,
        "dollar_volume": dollar_volume,
        "liquidity_fit_score": _clip01(liquidity_score if liquidity_score is not None else 0.5),
        "halt_status": str(quote.get("halt_status") or quote.get("trading_status") or "active").lower(),
    }


def _gate_state(
    quote: Mapping[str, Any],
    liquidity: Mapping[str, Any],
    borrow: Mapping[str, Any],
    risk: Mapping[str, Any],
    policy: Mapping[str, Any],
    exposure: Mapping[str, float],
) -> dict[str, Any]:
    hard_reasons: list[str] = []
    halt_status = str(quote.get("halt_status") or quote.get("trading_status") or "active").lower()
    if halt_status not in {"active", "open", "trading", "normal"}:
        hard_reasons.append("halt_status_not_active")
    if _truthy(risk.get("kill_switch_active")) or _truthy(policy.get("kill_switch_active")):
        hard_reasons.append("kill_switch_active")
    if _truthy(risk.get("risk_budget_hard_block")) or _truthy(policy.get("risk_budget_hard_block")):
        hard_reasons.append("risk_budget_hard_block")
    if _truthy(policy.get("symbol_trading_restricted")) or _truthy(policy.get("trading_restricted")):
        hard_reasons.append("symbol_trading_restricted")
    if _truthy(policy.get("underlying_event_hard_block")):
        hard_reasons.append("underlying_event_hard_block")
    spread_bps = _first_float(liquidity, "spread_bps")
    dollar_volume = _first_float(liquidity, "dollar_volume", "avg_dollar_volume")
    if _truthy(liquidity.get("liquidity_hard_fail")) or (spread_bps is not None and spread_bps > 250) or (dollar_volume is not None and dollar_volume < 50_000):
        hard_reasons.append("liquidity_hard_fail")
    wants_short = exposure["target_underlying_exposure_score"] < -MATERIAL_GAP_THRESHOLD
    if wants_short and not _direct_short_allowed(borrow, policy):
        hard_reasons.append("short_borrow_failed_for_direct_short")
    risk_fit = _first_float(risk, "risk_budget_fit_score", "6_risk_budget_fit_score", "risk_fit_score")
    return {
        "hard_blocked": bool(hard_reasons),
        "hard_gate_reason_codes": hard_reasons,
        "risk_budget_fit_score": _clip01(risk_fit if risk_fit is not None else 1.0),
    }


def _horizon_payload(
    horizon: str,
    alpha: Mapping[str, Any],
    projection: Mapping[str, Any],
    exposure: Mapping[str, float],
    quote_state: Mapping[str, Any],
    gate_state: Mapping[str, Any],
    borrow: Mapping[str, Any],
    risk: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    suffix = _suffix(horizon)
    alpha_confidence = _score(alpha, f"5_alpha_confidence_score_{suffix}", "5_alpha_confidence_score", default=0.5)
    expected_return = _first_float(alpha, f"5_expected_return_score_{suffix}", "5_expected_return_score")
    if expected_return is None:
        expected_return = _first_float(projection, f"6_expected_position_utility_score_{suffix}", "6_expected_position_utility_score")
    if expected_return is None:
        expected_return = 0.0
    projection_confidence = _score(projection, f"6_projection_confidence_score_{suffix}", "6_projection_confidence_score", default=0.5)
    risk_fit = _score(projection, f"6_risk_budget_fit_score_{suffix}", "6_risk_budget_fit_score", default=gate_state["risk_budget_fit_score"])
    cost_to_adjust = _score(projection, f"6_cost_to_adjust_position_score_{suffix}", "6_cost_to_adjust_position_score", default=0.2)
    stability = _score(projection, f"6_position_state_stability_score_{suffix}", "6_position_state_stability_score", default=0.6)
    path_quality = _score(alpha, f"5_path_quality_score_{suffix}", "5_path_quality_score", default=0.6)
    reversal_risk = _score(alpha, f"5_reversal_risk_score_{suffix}", "5_reversal_risk_score", default=0.25)
    drawdown_risk = _score(alpha, f"5_drawdown_risk_score_{suffix}", "5_drawdown_risk_score", default=0.25)
    liquidity_fit = _clip01(_score({}, "missing", default=quote_state.get("liquidity_fit_score")))

    gap = exposure["underlying_exposure_gap_score"]
    target = exposure["target_underlying_exposure_score"]
    action_direction = 0.0 if abs(gap) < MATERIAL_GAP_THRESHOLD else (1.0 if gap > 0 else -1.0)
    if target < -MATERIAL_GAP_THRESHOLD and not _direct_short_allowed(borrow, policy):
        action_direction = -0.5

    hard_blocked = bool(gate_state["hard_blocked"])
    soft_reasons: list[str] = []
    if alpha_confidence < 0.35:
        soft_reasons.append("alpha_confidence_marginal")
    if projection_confidence < 0.35:
        soft_reasons.append("projection_confidence_marginal")
    if abs(gap) < MATERIAL_GAP_THRESHOLD:
        soft_reasons.append("position_gap_small")
    if cost_to_adjust > 0.65:
        soft_reasons.append("cost_pressure_high")
    if reversal_risk > 0.65:
        soft_reasons.append("reversal_risk_elevated")
    if drawdown_risk > 0.65:
        soft_reasons.append("drawdown_risk_elevated")
    if path_quality < 0.35:
        soft_reasons.append("path_quality_weak")
    if liquidity_fit < 0.35:
        soft_reasons.append("liquidity_marginal")

    gate_components = [alpha_confidence, projection_confidence, risk_fit, liquidity_fit, _invert01(cost_to_adjust)]
    trade_eligibility = 0.0 if hard_blocked else _geometric_score(gate_components, default=0.0)
    raw_intensity = abs(gap) * alpha_confidence * projection_confidence * risk_fit * stability * liquidity_fit * _invert01(cost_to_adjust) * _invert01(drawdown_risk) * _invert01(reversal_risk)
    trade_intensity = 0.0 if hard_blocked else _clip01(raw_intensity)
    entry_quality = 0.0 if hard_blocked else _clip01(_geometric_score([liquidity_fit, path_quality, _invert01(cost_to_adjust), _invert01(reversal_risk)], default=0.0))
    adverse_risk = _clip01(_average([drawdown_risk, reversal_risk, cost_to_adjust]) or 0.0)
    expected_return_score = _clip_signed(expected_return)
    reward_risk = _clip01((abs(expected_return_score) * path_quality * _invert01(adverse_risk)) / 0.05) if expected_return_score else 0.0
    holding_time_fit = _clip01(_average([projection_confidence, stability, path_quality, liquidity_fit]) or 0.0)
    confidence = _clip01(_geometric_score([trade_eligibility, entry_quality, reward_risk, holding_time_fit, _invert01(adverse_risk)], default=0.0))

    return {
        "horizon": horizon,
        "trade_eligibility_score": trade_eligibility,
        "action_direction_score": _clip_signed(action_direction),
        "trade_intensity_score": trade_intensity,
        "entry_quality_score": entry_quality,
        "expected_return_score": expected_return_score,
        "adverse_risk_score": adverse_risk,
        "reward_risk_score": reward_risk,
        "liquidity_fit_score": liquidity_fit,
        "holding_time_fit_score": holding_time_fit,
        "action_confidence_score": confidence,
        "alpha_confidence_score": alpha_confidence,
        "projection_confidence_score": projection_confidence,
        "cost_to_adjust_position_score": cost_to_adjust,
        "path_quality_score": path_quality,
        "reversal_risk_score": reversal_risk,
        "drawdown_risk_score": drawdown_risk,
        "risk_budget_fit_score": risk_fit,
        "soft_gate_reason_codes": soft_reasons,
    }


def _dominant_horizon(horizon_payloads: Mapping[str, Mapping[str, Any]], projection: Mapping[str, Any]) -> str:
    explicit = str(projection.get("6_dominant_projection_horizon") or "").strip()
    if explicit in HORIZONS:
        return explicit
    ranked = sorted(
        HORIZONS,
        key=lambda horizon: (
            horizon_payloads[horizon]["action_confidence_score"] * max(horizon_payloads[horizon]["trade_intensity_score"], MIN_TRADE_INTENSITY),
            HORIZON_MINUTES[horizon],
        ),
        reverse=True,
    )
    return ranked[0]


def _resolve_action(
    exposure: Mapping[str, float],
    dominant: Mapping[str, Any],
    gate_state: Mapping[str, Any],
    borrow: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, str]:
    current = exposure["effective_current_underlying_exposure_score"]
    target = exposure["target_underlying_exposure_score"]
    gap = exposure["underlying_exposure_gap_score"]
    direct_short_allowed = _direct_short_allowed(borrow, policy)
    current_state = "flat"
    if current > MATERIAL_GAP_THRESHOLD:
        current_state = "long"
    elif current < -MATERIAL_GAP_THRESHOLD:
        current_state = "short"

    if gate_state["hard_blocked"]:
        hard_reasons = set(gate_state.get("hard_gate_reason_codes", []))
        only_short_borrow_block = hard_reasons == {"short_borrow_failed_for_direct_short"}
        if only_short_borrow_block and current_state == "flat" and target < -MATERIAL_GAP_THRESHOLD:
            return {"planned_underlying_action_type": "bearish_underlying_path_but_no_short_allowed", "action_side": "bearish_no_direct_short"}
        reducing_long = current_state == "long" and target < current - MATERIAL_GAP_THRESHOLD
        reducing_short = current_state == "short" and target > current + MATERIAL_GAP_THRESHOLD
        if reducing_long:
            return {"planned_underlying_action_type": "close_long" if target <= MATERIAL_GAP_THRESHOLD else "reduce_long", "action_side": "long_reduction"}
        if reducing_short:
            return {"planned_underlying_action_type": "cover_short" if target >= -MATERIAL_GAP_THRESHOLD else "reduce_short", "action_side": "short_reduction"}
        return {"planned_underlying_action_type": "no_trade", "action_side": "none"}

    if abs(gap) < MATERIAL_GAP_THRESHOLD or dominant["trade_intensity_score"] < MIN_TRADE_INTENSITY:
        return {"planned_underlying_action_type": "maintain" if current_state != "flat" else "no_trade", "action_side": "none"}

    if current_state == "flat":
        if gap > 0:
            return {"planned_underlying_action_type": "open_long", "action_side": "long"}
        if direct_short_allowed:
            return {"planned_underlying_action_type": "open_short", "action_side": "short"}
        return {"planned_underlying_action_type": "bearish_underlying_path_but_no_short_allowed", "action_side": "bearish_no_direct_short"}

    if current_state == "long":
        if target <= MATERIAL_GAP_THRESHOLD:
            return {"planned_underlying_action_type": "close_long", "action_side": "long_reduction"}
        if gap > 0:
            return {"planned_underlying_action_type": "increase_long", "action_side": "long"}
        return {"planned_underlying_action_type": "reduce_long", "action_side": "long_reduction"}

    if target >= -MATERIAL_GAP_THRESHOLD:
        return {"planned_underlying_action_type": "cover_short", "action_side": "short_reduction"}
    if gap < 0:
        return {"planned_underlying_action_type": "increase_short", "action_side": "short"}
    return {"planned_underlying_action_type": "reduce_short", "action_side": "short_reduction"}


def _entry_plan(action: Mapping[str, str], dominant: Mapping[str, Any], quote: Mapping[str, Any], available_time: str) -> dict[str, Any]:
    action_type = action["planned_underlying_action_type"]
    reference = float(quote["reference_price"])
    spread_fraction = ((quote.get("spread_bps") or 10.0) / 10_000.0)
    confidence = dominant["action_confidence_score"]
    entry_quality = dominant["entry_quality_score"]
    if action_type in {"no_trade", "bearish_underlying_path_but_no_short_allowed"}:
        style = "no_entry"
    elif action_type == "maintain":
        style = "maintain_existing_entry"
    elif confidence >= 0.75 and entry_quality >= 0.70:
        style = "marketable_review"
    elif entry_quality >= 0.55:
        style = "limit_near_mid"
    elif dominant["path_quality_score"] >= 0.45:
        style = "limit_or_pullback"
    else:
        style = "wait_for_pullback"

    side = action["action_side"]
    side_sign = 1 if side == "long" else -1 if side == "short" else 0
    expected_entry = reference if side_sign == 0 else reference * (1 + side_sign * spread_fraction * 0.25)
    worst_buffer = max(spread_fraction * 2.0, 0.0025)
    if side_sign > 0:
        worst = reference * (1 + worst_buffer)
        chase = reference * (1 + worst_buffer * 1.75)
        limit_direction = "upper_bound_for_long"
    elif side_sign < 0:
        worst = reference * (1 - worst_buffer)
        chase = reference * (1 - worst_buffer * 1.75)
        limit_direction = "lower_bound_for_short"
    else:
        worst = None
        chase = None
        limit_direction = "none"
    expiry = _iso(_parse_time(available_time) + timedelta(minutes=min(HORIZON_MINUTES[dominant["horizon"]], 60)))
    return {
        "entry_style": style,
        "reference_price": _round_price(reference),
        "expected_entry_price": _round_price(expected_entry),
        "worst_acceptable_entry_price": _round_price(worst),
        "do_not_chase_price": _round_price(chase),
        "entry_price_limit_direction": limit_direction,
        "entry_expiration_time": expiry if style not in {"no_entry", "maintain_existing_entry"} else None,
        "entry_quality_score": dominant["entry_quality_score"],
    }


def _price_path(action: Mapping[str, str], dominant: Mapping[str, Any], quote: Mapping[str, Any]) -> dict[str, Any]:
    reference = float(quote["reference_price"])
    side = action["action_side"]
    side_sign = 1 if side == "long" else -1 if side == "short" else 0
    horizon = dominant["horizon"]
    expected_return = abs(dominant["expected_return_score"])
    favorable = max(expected_return, DEFAULT_TARGET_RETURN_BY_HORIZON[horizon] * max(dominant["trade_intensity_score"], 0.5)) if side_sign else 0.0
    adverse = -max(DEFAULT_ADVERSE_MOVE_BY_HORIZON[horizon] * (1.0 + dominant["adverse_risk_score"]), 0.0025) if side_sign else 0.0
    target = reference * (1 + side_sign * favorable) if side_sign else reference
    low = target * (1 - abs(favorable) * 0.25) if side_sign > 0 else target * (1 - abs(favorable) * 0.15) if side_sign < 0 else reference
    high = target * (1 + abs(favorable) * 0.15) if side_sign > 0 else target * (1 + abs(favorable) * 0.25) if side_sign < 0 else reference
    return {
        "underlying_path_direction": "bullish" if side_sign > 0 else "bearish" if side_sign < 0 else "neutral",
        "expected_holding_time_minutes": HORIZON_MINUTES[horizon],
        "expected_holding_time_label": "1_session" if horizon == "390min" else horizon,
        "expected_target_price": _round_price(target),
        "target_price_low": _round_price(min(low, high)),
        "target_price_high": _round_price(max(low, high)),
        "expected_favorable_move_pct": round(favorable, 6),
        "expected_adverse_move_pct": round(adverse, 6),
        "path_quality_score": dominant["path_quality_score"],
        "reversal_risk_score": dominant["reversal_risk_score"],
        "drawdown_risk_score": dominant["drawdown_risk_score"],
    }


def _risk_plan(action: Mapping[str, str], dominant: Mapping[str, Any], quote: Mapping[str, Any], path: Mapping[str, Any]) -> dict[str, Any]:
    reference = float(quote["reference_price"])
    side = action["action_side"]
    side_sign = 1 if side == "long" else -1 if side == "short" else 0
    favorable = abs(float(path["expected_favorable_move_pct"]))
    adverse = abs(float(path["expected_adverse_move_pct"]))
    if side_sign == 0:
        return {
            "partial_take_profit_price": None,
            "take_profit_price": None,
            "stop_loss_price": None,
            "thesis_invalidation_price": None,
            "time_stop_minutes": HORIZON_MINUTES[dominant["horizon"]],
            "expected_favorable_move_pct": 0.0,
            "expected_adverse_move_pct": 0.0,
            "reward_risk_ratio": 0.0,
            "risk_plan_reason_codes": ["no_directional_underlying_risk_plan"],
        }
    partial = reference * (1 + side_sign * favorable * 0.55)
    take = reference * (1 + side_sign * favorable)
    stop = reference * (1 - side_sign * adverse)
    invalidation = reference * (1 - side_sign * adverse * 1.20)
    reward_risk = favorable / adverse if adverse else None
    return {
        "partial_take_profit_price": _round_price(partial),
        "take_profit_price": _round_price(take),
        "stop_loss_price": _round_price(stop),
        "thesis_invalidation_price": _round_price(invalidation),
        "time_stop_minutes": HORIZON_MINUTES[dominant["horizon"]],
        "expected_favorable_move_pct": round(favorable, 6),
        "expected_adverse_move_pct": round(-adverse, 6),
        "reward_risk_ratio": None if reward_risk is None else round(reward_risk, 4),
        "risk_plan_reason_codes": ["side_neutral_price_path_projected", f"{dominant['horizon']}_dominant_horizon"],
    }


def _exposure_plan(exposure: Mapping[str, float], dominant: Mapping[str, Any], action: Mapping[str, str], quote: Mapping[str, Any]) -> dict[str, Any]:
    gap = exposure["underlying_exposure_gap_score"]
    action_type = action["planned_underlying_action_type"]
    active = action_type not in {"maintain", "no_trade", "bearish_underlying_path_but_no_short_allowed"}
    planned_increment = _clip_signed(gap * dominant["trade_intensity_score"]) if active else 0.0
    reference = float(quote["reference_price"])
    notional_basis = 100_000.0
    planned_notional = abs(planned_increment) * notional_basis
    planned_quantity = int(planned_notional / reference) if reference > 0 else 0
    return {
        "target_underlying_exposure_score": exposure["target_underlying_exposure_score"],
        "current_underlying_exposure_score": exposure["current_underlying_exposure_score"],
        "pending_underlying_exposure_score": exposure["pending_underlying_exposure_score"],
        "pending_fill_probability_estimate": exposure["pending_fill_probability_estimate"],
        "pending_adjusted_underlying_exposure_score": exposure["pending_adjusted_underlying_exposure_score"],
        "effective_current_underlying_exposure_score": exposure["effective_current_underlying_exposure_score"],
        "underlying_exposure_gap_score": gap,
        "planned_incremental_exposure_score": round(planned_increment, 6),
        "planned_notional_usd": round(planned_notional, 2),
        "planned_quantity": planned_quantity,
        "scale_in_policy": "single_plan_review" if dominant["trade_intensity_score"] >= 0.25 else "small_probe_or_wait",
    }


def _layer8_handoff(entry: Mapping[str, Any], path: Mapping[str, Any], risk: Mapping[str, Any], dominant: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "underlying_path_direction": path["underlying_path_direction"],
        "expected_entry_price": entry["expected_entry_price"],
        "expected_target_price": path["expected_target_price"],
        "target_price_low": path["target_price_low"],
        "target_price_high": path["target_price_high"],
        "stop_loss_price": risk["stop_loss_price"],
        "thesis_invalidation_price": risk["thesis_invalidation_price"],
        "expected_holding_time_minutes": path["expected_holding_time_minutes"],
        "path_quality_score": path["path_quality_score"],
        "reversal_risk_score": path["reversal_risk_score"],
        "drawdown_risk_score": path["drawdown_risk_score"],
        "expected_favorable_move_pct": path["expected_favorable_move_pct"],
        "expected_adverse_move_pct": path["expected_adverse_move_pct"],
        "entry_price_assumption": entry["entry_style"],
        "underlying_action_confidence_score": dominant["action_confidence_score"],
    }


def _reason_codes(gate_state: Mapping[str, Any], dominant: Mapping[str, Any], action: Mapping[str, str]) -> list[str]:
    reasons: list[str] = []
    reasons.extend(gate_state["hard_gate_reason_codes"])
    reasons.extend(dominant["soft_gate_reason_codes"])
    action_type = action["planned_underlying_action_type"]
    if action_type in {"open_long", "increase_long", "open_short", "increase_short"}:
        reasons.append("material_resolved_position_gap")
    if action_type in {"close_long", "cover_short"}:
        reasons.append("opposite_exposure_detected")
        reasons.append("close_then_reassess_candidate")
    if action_type == "maintain":
        reasons.append("existing_state_remains_valid_or_adjustment_not_worth_cost")
    if action_type == "no_trade":
        reasons.append("no_new_underlying_operation")
    if action_type == "bearish_underlying_path_but_no_short_allowed":
        reasons.append("direct_short_not_allowed")
    reasons.append(f"{dominant['horizon']}_projection_dominant")
    return _dedupe(reasons)


def _direct_short_allowed(borrow: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    if _truthy(policy.get("direct_short_allowed")) or _truthy(borrow.get("direct_short_allowed")):
        return True
    status = str(borrow.get("short_borrow_status") or borrow.get("borrow_status") or "").lower()
    return status in {"available", "easy_to_borrow", "etb", "ok"}


def _score(mapping: Mapping[str, Any], *keys: str, default: float | None = None) -> float:
    value = _first_float(mapping, *keys)
    if value is None:
        return _clip01(default if default is not None else 0.0)
    return _clip01(value)


def _first_float(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return value
    return None


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        output = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(output) or math.isinf(output):
        return None
    return output


def _average(values: Iterable[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _geometric_score(values: Iterable[float | None], *, default: float = 0.0) -> float:
    clean = [_clip01(value) for value in values if value is not None]
    if not clean:
        return default
    product = 1.0
    for value in clean:
        product *= max(value, 0.0)
    return _clip01(product ** (1.0 / len(clean)))


def _invert01(value: float | None) -> float:
    if value is None:
        return 0.0
    return _clip01(1.0 - value)


def _clip01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _clip_signed(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(-1.0, min(1.0, float(value)))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active", "blocked", "fail", "failed"}


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _suffix(horizon: str) -> str:
    return horizon.replace("min", "min")


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("decision_time") or row.get("tradeable_time"))


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        parsed = datetime(1970, 1, 1, tzinfo=ET)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ET)
    return value.astimezone(ET).isoformat()


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden Layer 7 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

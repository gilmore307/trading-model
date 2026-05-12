"""Deterministic OptionExpressionModel V1 scaffold.

Layer 8 consumes the Layer 7 underlying thesis plus point-in-time option-chain
context and emits an offline ``option_expression_plan`` / ``expression_vector``.
It can select an expression type, option right, contract reference, and contract
constraints. It must not place orders, route orders, or mutate broker/account
state.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import EXPRESSION_TYPES, FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 8 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    underlying_plan = _payload(row, "underlying_action_plan")
    handoff = _payload(underlying_plan, "handoff_to_layer_8") or _payload(row, "layer_8_underlying_handoff")
    market = _payload(row, "market_context_state")
    event = _payload(row, "event_context_vector")
    policy = _payload(row, "option_expression_policy")
    pending = _pending_option_context(row)
    candidates = _candidate_rows(row)
    replay_context = _replay_context(row)

    direction = _underlying_direction(underlying_plan, handoff)
    expression_type, option_right = _expression_type(direction, underlying_plan, policy, pending)
    scored_candidates = [_score_candidate(candidate, option_right, handoff, market, event, policy) for candidate in candidates]
    eligible_candidates = [candidate for candidate in scored_candidates if candidate["option_right"] == option_right and candidate["eligible"]]
    selected = max(eligible_candidates, key=lambda candidate: candidate["contract_fit_score"], default=None)

    horizon_payloads = {
        horizon: _horizon_payload(horizon, expression_type, direction, selected, handoff, market, event, policy)
        for horizon in HORIZONS
    }
    dominant_horizon = _dominant_horizon(horizon_payloads, underlying_plan)
    dominant = horizon_payloads[dominant_horizon]
    if expression_type != "no_option_expression" and selected is None:
        expression_type = "no_option_expression"
        option_right = "none"
        dominant = {**dominant, "expression_eligibility_score": 0.0, "expression_confidence_score": 0.0}

    expression_plan_ref = _stable_id("oep", target_candidate_id, available_time, model_version)
    score_payload: dict[str, Any] = {}
    for horizon, payload in horizon_payloads.items():
        suffix = _suffix(horizon)
        score_payload.update(
            {
                f"8_option_expression_eligibility_score_{suffix}": payload["expression_eligibility_score"],
                f"8_option_expression_direction_score_{suffix}": payload["expression_direction_score"],
                f"8_option_contract_fit_score_{suffix}": payload["contract_fit_score"],
                f"8_option_liquidity_fit_score_{suffix}": payload["liquidity_fit_score"],
                f"8_option_iv_fit_score_{suffix}": payload["iv_fit_score"],
                f"8_option_greek_fit_score_{suffix}": payload["greek_fit_score"],
                f"8_option_reward_risk_score_{suffix}": payload["reward_risk_score"],
                f"8_option_theta_risk_score_{suffix}": payload["theta_risk_score"],
                f"8_option_fill_quality_score_{suffix}": payload["fill_quality_score"],
                f"8_option_expression_confidence_score_{suffix}": payload["expression_confidence_score"],
            }
        )
    reason_codes = _reason_codes(expression_type, selected, dominant, scored_candidates, option_right, policy, underlying_plan, pending)
    no_option_reason_codes = [code for code in reason_codes if expression_type == "no_option_expression"]
    resolved_payload = {
        "8_resolved_expression_type": expression_type,
        "8_resolved_option_right": option_right,
        "8_resolved_dominant_horizon": dominant_horizon,
        "8_resolved_selected_contract_ref": None if selected is None else selected["contract_ref"],
        "8_resolved_contract_fit_score": dominant["contract_fit_score"],
        "8_resolved_expression_confidence_score": dominant["expression_confidence_score"],
        "8_resolved_no_option_reason_codes": no_option_reason_codes,
        "8_resolved_reason_codes": reason_codes,
    }
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "underlying_action_plan_ref": row.get("underlying_action_plan_ref") or underlying_plan.get("underlying_action_plan_ref"),
        "option_expression_plan_ref": expression_plan_ref,
        "option_chain_snapshot_ref": replay_context["option_chain_snapshot_ref"],
        "option_quote_available_time": replay_context["option_quote_available_time"],
        "underlying_quote_snapshot_ref": replay_context["underlying_quote_snapshot_ref"],
        "underlying_reference_price": replay_context["underlying_reference_price"],
        "pending_option_exposure_context": pending,
        **score_payload,
        **resolved_payload,
        "expression_vector": {**score_payload, **resolved_payload},
        "option_expression_plan": {
            "selected_expression_type": expression_type,
            "selected_option_right": option_right,
            "dominant_horizon": dominant_horizon,
            "option_chain_snapshot_ref": replay_context["option_chain_snapshot_ref"],
            "option_quote_available_time": replay_context["option_quote_available_time"],
            "underlying_quote_snapshot_ref": replay_context["underlying_quote_snapshot_ref"],
            "underlying_reference_price": replay_context["underlying_reference_price"],
            "replay_context": replay_context,
            "selected_contract": _selected_contract_payload(selected),
            "contract_constraints": _contract_constraints(option_right, handoff, policy),
            "premium_risk_plan": _premium_risk_plan(selected, handoff, dominant, policy),
            "underlying_thesis_ref": row.get("underlying_action_plan_ref") or underlying_plan.get("underlying_action_plan_ref"),
            "underlying_path_assumptions": handoff,
            "reason_codes": reason_codes,
            "diagnostics": {
                "candidate_count_before_filter": len(candidates),
                "candidate_count_after_filter": len(eligible_candidates),
                "pending_option_exposure_context": pending,
                "no_future_label_used": True,
                "scored_candidates": scored_candidates,
                "horizon_scores": horizon_payloads,
            },
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _candidate_rows(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = row.get("option_contract_candidates") or row.get("option_chain_snapshot") or row.get("option_chain") or []
    if isinstance(candidates, str):
        candidates = _coerce_payload(candidates)
    if isinstance(candidates, Mapping):
        candidates = [candidates]
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)] if isinstance(candidates, Sequence) else []


def _underlying_direction(underlying_plan: Mapping[str, Any], handoff: Mapping[str, Any]) -> str:
    direction = str(handoff.get("underlying_path_direction") or "").lower()
    if direction in {"bullish", "bearish", "neutral"}:
        return direction
    side = str(underlying_plan.get("action_side") or underlying_plan.get("7_resolved_action_side") or "").lower()
    if side == "long":
        return "bullish"
    if side in {"short", "bearish_no_direct_short"}:
        return "bearish"
    return "neutral"


def _expression_type(direction: str, underlying_plan: Mapping[str, Any], policy: Mapping[str, Any], pending: Mapping[str, Any]) -> tuple[str, str]:
    if str(policy.get("option_expression_allowed") or policy.get("allow_option_expression") or "true").lower() in {"false", "0", "no", "blocked"}:
        return "no_option_expression", "none"
    if pending.get("has_pending_option_exposure"):
        return "no_option_expression", "none"
    action_type = str(underlying_plan.get("planned_underlying_action_type") or "").lower()
    if action_type in {"maintain", "no_trade"}:
        return "no_option_expression", "none"
    if direction == "bullish":
        return "long_call", "call"
    if direction == "bearish":
        return "long_put", "put"
    return "no_option_expression", "none"


def _score_candidate(
    candidate: Mapping[str, Any],
    required_right: str,
    handoff: Mapping[str, Any],
    market: Mapping[str, Any],
    event: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    right = _normalize_right(candidate.get("option_right") or candidate.get("right"))
    bid = _first_float(candidate, "bid_price", "bid") or 0.0
    ask = _first_float(candidate, "ask_price", "ask") or 0.0
    mid = _first_float(candidate, "mid_price", "mid")
    if mid is None and bid > 0 and ask > 0:
        mid = (bid + ask) / 2.0
    if mid is None:
        mid = _first_float(candidate, "mark_price", "last_price") or 0.0
    spread_pct = (ask - bid) / mid if mid > 0 and ask >= bid else 1.0
    max_spread_pct = _score(policy, "max_option_spread_pct", "max_spread_pct_mid", default=0.18)
    dte = _first_float(candidate, "dte", "days_to_expiration") or 0.0
    delta = _first_float(candidate, "delta") or 0.0
    theta = abs(_first_float(candidate, "theta") or 0.0)
    vega = abs(_first_float(candidate, "vega") or 0.0)
    iv_rank = _score(candidate, "iv_rank", "implied_volatility_rank", default=0.50)
    volume = _first_float(candidate, "volume", "day_volume") or 0.0
    open_interest = _first_float(candidate, "open_interest") or 0.0
    quote_age_seconds = _first_float(candidate, "quote_age_seconds")
    min_volume = _first_float(policy, "min_volume") or 0.0
    min_open_interest = _first_float(policy, "min_open_interest") or 0.0
    max_quote_age = _first_float(policy, "max_quote_age_seconds") or 300.0
    min_abs_delta = _first_float(policy, "min_abs_delta", "min_option_abs_delta") or 0.35
    max_abs_delta = _first_float(policy, "max_abs_delta", "max_option_abs_delta") or 0.65
    min_dte, max_dte = _preferred_dte_range(float(handoff.get("expected_holding_time_minutes") or 390.0))
    target_dte = _target_dte(float(handoff.get("expected_holding_time_minutes") or 390.0))
    dte_fit = _triangular_fit(dte, target_dte, max((max_dte - min_dte) / 2.0, 3.0))
    delta_fit = _triangular_fit(abs(delta), _target_delta(handoff, event), 0.25)
    liquidity_fit = _clip01(0.40 * (1.0 - min(spread_pct / max(max_spread_pct, 0.01), 1.0)) + 0.30 * _clip01(volume / 250.0) + 0.30 * _clip01(open_interest / 1000.0))
    iv_fit = _clip01(1.0 - max(iv_rank - _iv_rank_ceiling(market, event, policy), 0.0) / 0.50)
    theta_risk = _clip01(theta / max(mid, 0.01) * min(dte, 30.0) / 3.0) if mid > 0 else 1.0
    greek_fit = _clip01(0.55 * delta_fit + 0.25 * (1.0 - theta_risk) + 0.20 * _clip01(vega / max(mid, 0.01) if mid > 0 else 0.0))
    fill_quality = _clip01(0.70 * liquidity_fit + 0.30 * (1.0 - min(spread_pct / max(max_spread_pct, 0.01), 1.0)))
    favorable_move = abs(_first_float(handoff, "expected_favorable_move_pct") or 0.0)
    adverse_move = abs(_first_float(handoff, "expected_adverse_move_pct") or 0.0)
    expected_option_gain = abs(delta) * favorable_move / max(mid / max(_first_float(handoff, "expected_entry_price") or 1.0, 1.0), 0.001)
    expected_option_loss = max(abs(delta) * adverse_move / max(mid / max(_first_float(handoff, "expected_entry_price") or 1.0, 1.0), 0.001), 0.05)
    reward_risk = _clip01(expected_option_gain / max(expected_option_loss * 2.0, 0.01))
    contract_fit = _clip01(0.22 * dte_fit + 0.20 * greek_fit + 0.20 * liquidity_fit + 0.14 * iv_fit + 0.14 * reward_risk + 0.10 * fill_quality)
    adjusted = _truthy(candidate.get("is_adjusted_contract") or candidate.get("adjusted_contract"))
    quote_fresh = quote_age_seconds is None or quote_age_seconds <= max_quote_age
    strike = _first_float(candidate, "strike")
    target_range_ok = _target_range_ok(required_right, strike, handoff)
    hard_filter_fail_reason_codes: list[str] = []
    if right != required_right:
        hard_filter_fail_reason_codes.append("option_right_mismatch")
    if bid <= 0 or ask <= 0 or mid <= 0:
        hard_filter_fail_reason_codes.append("non_positive_quote")
    if ask < bid:
        hard_filter_fail_reason_codes.append("crossed_or_invalid_quote")
    if spread_pct > max_spread_pct:
        hard_filter_fail_reason_codes.append("spread_too_wide")
    if not min_dte <= dte <= max_dte:
        hard_filter_fail_reason_codes.append("dte_outside_policy_range")
    if not min_abs_delta <= abs(delta) <= max_abs_delta:
        hard_filter_fail_reason_codes.append("delta_outside_policy_range")
    if volume < min_volume:
        hard_filter_fail_reason_codes.append("volume_below_minimum")
    if open_interest < min_open_interest:
        hard_filter_fail_reason_codes.append("open_interest_below_minimum")
    if not quote_fresh:
        hard_filter_fail_reason_codes.append("stale_option_quote")
    if adjusted:
        hard_filter_fail_reason_codes.append("adjusted_contract_excluded")
    if not target_range_ok:
        hard_filter_fail_reason_codes.append("strike_outside_underlying_target_range")
    eligible = not hard_filter_fail_reason_codes
    return {
        "contract_ref": str(candidate.get("contract_ref") or candidate.get("option_contract_ref") or candidate.get("symbol") or "").strip() or _stable_id("contract", right, dte, delta, mid),
        "option_right": right,
        "quote_snapshot_ref": candidate.get("quote_snapshot_ref") or candidate.get("option_quote_snapshot_ref"),
        "quote_available_time": candidate.get("quote_available_time") or candidate.get("option_quote_available_time"),
        "expiration": candidate.get("expiration"),
        "strike": _round_optional(strike),
        "moneyness": _round_optional(_first_float(candidate, "moneyness")),
        "contract_multiplier": _round_optional(_first_float(candidate, "contract_multiplier")),
        "exercise_style": candidate.get("exercise_style"),
        "settlement_type": candidate.get("settlement_type"),
        "is_weekly": candidate.get("is_weekly"),
        "is_monthly": candidate.get("is_monthly"),
        "is_adjusted_contract": adjusted,
        "last_trade_time": candidate.get("last_trade_time"),
        "quote_age_seconds": _round_optional(quote_age_seconds),
        "dte": round(dte, 6),
        "delta": round(delta, 6),
        "gamma": _round_optional(_first_float(candidate, "gamma")),
        "theta": _round_optional(_first_float(candidate, "theta")),
        "vega": _round_optional(_first_float(candidate, "vega")),
        "iv": _round_optional(_first_float(candidate, "iv", "implied_volatility")),
        "iv_rank": round(iv_rank, 6),
        "bid_price": _round_price(bid),
        "ask_price": _round_price(ask),
        "mid_price": _round_price(mid),
        "bid_size": _round_optional(_first_float(candidate, "bid_size")),
        "ask_size": _round_optional(_first_float(candidate, "ask_size")),
        "volume": round(volume, 6),
        "open_interest": round(open_interest, 6),
        "spread_abs": _round_price(ask - bid if ask >= bid else None),
        "spread_pct": round(spread_pct, 6),
        "spread_pct_mid": round(spread_pct, 6),
        "intrinsic_value": _round_price(_first_float(candidate, "intrinsic_value")),
        "extrinsic_value": _round_price(_first_float(candidate, "extrinsic_value")),
        "breakeven_price": _round_price(_first_float(candidate, "breakeven_price")),
        "theoretical_value": _round_price(_first_float(candidate, "theoretical_value")),
        "dte_fit_score": round(dte_fit, 6),
        "liquidity_fit_score": round(liquidity_fit, 6),
        "iv_fit_score": round(iv_fit, 6),
        "greek_fit_score": round(greek_fit, 6),
        "theta_risk_score": round(theta_risk, 6),
        "fill_quality_score": round(fill_quality, 6),
        "reward_risk_score": round(reward_risk, 6),
        "contract_fit_score": round(contract_fit if eligible else contract_fit * 0.25, 6),
        "eligible": eligible,
        "hard_filter_fail_reason_codes": hard_filter_fail_reason_codes,
    }


def _horizon_payload(
    horizon: str,
    expression_type: str,
    direction: str,
    selected: Mapping[str, Any] | None,
    handoff: Mapping[str, Any],
    market: Mapping[str, Any],
    event: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    if expression_type == "no_option_expression" or selected is None:
        return {
            "expression_eligibility_score": 0.0,
            "expression_direction_score": 0.0,
            "contract_fit_score": 0.0,
            "liquidity_fit_score": 0.0,
            "iv_fit_score": 0.0,
            "greek_fit_score": 0.0,
            "reward_risk_score": 0.0,
            "theta_risk_score": 0.0,
            "fill_quality_score": 0.0,
            "expression_confidence_score": 0.0,
        }
    path_quality = _score(handoff, "path_quality_score", default=0.5)
    reversal = _score(handoff, "reversal_risk_score", default=0.35)
    drawdown = _score(handoff, "drawdown_risk_score", default=0.35)
    market_liquidity = _score(market, "1_market_liquidity_support_score", default=0.65)
    event_uncertainty = _score(event, f"4_event_uncertainty_score_{_suffix(horizon)}", default=0.15)
    eligibility = _clip01(0.35 * selected["contract_fit_score"] + 0.20 * selected["liquidity_fit_score"] + 0.20 * selected["iv_fit_score"] + 0.15 * path_quality + 0.10 * market_liquidity)
    confidence = _clip01(0.35 * eligibility + 0.25 * selected["reward_risk_score"] + 0.20 * selected["fill_quality_score"] + 0.20 * path_quality - 0.20 * max(reversal, drawdown, event_uncertainty))
    direction_score = 1.0 if expression_type == "long_call" else -1.0 if expression_type == "long_put" else 0.0
    return {
        "expression_eligibility_score": round(eligibility, 6),
        "expression_direction_score": direction_score,
        "contract_fit_score": selected["contract_fit_score"],
        "liquidity_fit_score": selected["liquidity_fit_score"],
        "iv_fit_score": selected["iv_fit_score"],
        "greek_fit_score": selected["greek_fit_score"],
        "reward_risk_score": selected["reward_risk_score"],
        "theta_risk_score": selected["theta_risk_score"],
        "fill_quality_score": selected["fill_quality_score"],
        "expression_confidence_score": round(confidence, 6),
    }


def _dominant_horizon(horizon_payloads: Mapping[str, Mapping[str, Any]], underlying_plan: Mapping[str, Any]) -> str:
    resolved = str(underlying_plan.get("dominant_horizon") or underlying_plan.get("7_resolved_dominant_horizon") or "")
    if resolved in HORIZONS:
        return resolved
    return max(HORIZONS, key=lambda horizon: float(horizon_payloads[horizon]["expression_confidence_score"]))


def _selected_contract_payload(selected: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if selected is None:
        return None
    keys = (
        "contract_ref",
        "quote_snapshot_ref",
        "quote_available_time",
        "option_right",
        "expiration",
        "strike",
        "moneyness",
        "contract_multiplier",
        "exercise_style",
        "settlement_type",
        "is_weekly",
        "is_monthly",
        "is_adjusted_contract",
        "last_trade_time",
        "dte",
        "delta",
        "gamma",
        "theta",
        "vega",
        "iv",
        "iv_rank",
        "bid_price",
        "ask_price",
        "mid_price",
        "bid_size",
        "ask_size",
        "volume",
        "open_interest",
        "spread_abs",
        "spread_pct",
        "spread_pct_mid",
        "intrinsic_value",
        "extrinsic_value",
        "breakeven_price",
        "theoretical_value",
        "quote_age_seconds",
    )
    return {key: selected.get(key) for key in keys}


def _contract_constraints(option_right: str, handoff: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    holding = float(handoff.get("expected_holding_time_minutes") or 390.0)
    target_dte = _target_dte(holding)
    target_delta = _target_delta(handoff, {})
    min_dte, max_dte = _preferred_dte_range(holding)
    min_abs_delta = _first_float(policy, "min_abs_delta", "min_option_abs_delta") or 0.35
    max_abs_delta = _first_float(policy, "max_abs_delta", "max_option_abs_delta") or 0.65
    return {
        "allowed_option_right": option_right,
        "target_dte": target_dte if option_right != "none" else None,
        "preferred_dte_range": [min_dte, max_dte] if option_right != "none" else None,
        "min_dte": min_dte if option_right != "none" else None,
        "max_dte": max_dte if option_right != "none" else None,
        "target_abs_delta": target_delta if option_right != "none" else None,
        "min_abs_delta": min_abs_delta if option_right != "none" else None,
        "max_abs_delta": max_abs_delta if option_right != "none" else None,
        "max_spread_pct_mid": _score(policy, "max_option_spread_pct", "max_spread_pct_mid", default=0.18),
        "min_volume": _first_float(policy, "min_volume") or 0.0,
        "min_open_interest": _first_float(policy, "min_open_interest") or 0.0,
        "max_quote_age_seconds": _first_float(policy, "max_quote_age_seconds") or 300.0,
        "allow_0dte": False,
        "allow_adjusted_contract": False,
        "allow_single_leg_only": True,
        "allow_short_options": False,
        "iv_rank_ceiling": _iv_rank_ceiling({}, {}, policy) if option_right != "none" else None,
        "theta_decay_tolerance": "intraday_or_defined_risk_only" if holding <= 390 else "review_required",
    }


def _premium_risk_plan(selected: Mapping[str, Any] | None, handoff: Mapping[str, Any], dominant: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    if selected is None:
        return {
            "planned_premium_budget_score": 0.0,
            "planned_max_premium_at_risk_usd": 0.0,
            "premium_stop_pct": None,
            "premium_target_pct": None,
            "premium_time_stop_minutes": handoff.get("expected_holding_time_minutes"),
            "premium_decay_tolerance_score": 0.0,
            "max_loss_is_premium_paid_flag": True,
            "risk_plan_reason_codes": ["no_option_expression_selected"],
        }
    budget_score = _score(policy, "planned_premium_budget_score", default=0.18)
    return {
        "planned_premium_budget_score": budget_score,
        "planned_max_premium_at_risk_usd": _first_float(policy, "planned_max_premium_at_risk_usd") or 0.0,
        "premium_stop_pct": _first_float(policy, "premium_stop_pct") if _first_float(policy, "premium_stop_pct") is not None else -0.35,
        "premium_target_pct": _first_float(policy, "premium_target_pct") if _first_float(policy, "premium_target_pct") is not None else 0.70,
        "premium_time_stop_minutes": handoff.get("expected_holding_time_minutes"),
        "premium_decay_tolerance_score": _clip01(1.0 - dominant["theta_risk_score"]),
        "max_loss_is_premium_paid_flag": True,
        "expected_premium_reward_risk_score": dominant["reward_risk_score"],
        "theta_risk_score": dominant["theta_risk_score"],
        "risk_plan_reason_codes": ["defined_premium_risk", "offline_option_expression_only"],
    }


def _reason_codes(expression_type: str, selected: Mapping[str, Any] | None, dominant: Mapping[str, Any], scored_candidates: Sequence[Mapping[str, Any]], option_right: str, policy: Mapping[str, Any], underlying_plan: Mapping[str, Any], pending: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    action_type = str(underlying_plan.get("planned_underlying_action_type") or "").lower()
    if expression_type == "no_option_expression":
        reasons.append("no_option_expression_selected")
        if action_type in {"maintain", "no_trade"}:
            reasons.append(f"underlying_action_{action_type}")
        if pending.get("has_pending_option_exposure"):
            reasons.append("pending_option_exposure_detected")
    else:
        reasons.append(f"{expression_type}_selected")
    if selected is None and option_right != "none":
        reasons.append("no_eligible_option_contract_candidate")
    if not scored_candidates:
        reasons.append("missing_option_chain_candidates")
    if dominant.get("theta_risk_score", 0.0) >= 0.65:
        reasons.append("theta_risk_pressure")
    if dominant.get("iv_fit_score", 0.0) <= 0.35 and expression_type != "no_option_expression":
        reasons.append("iv_fit_downgrade")
    if str(policy.get("option_expression_allowed") or policy.get("allow_option_expression") or "true").lower() in {"false", "0", "no", "blocked"}:
        reasons.append("option_expression_policy_blocked")
    if scored_candidates and selected is None and expression_type == "no_option_expression":
        reasons.append("no_contract_passed_hard_filter")
        reasons.extend(_candidate_filter_reason_summary(scored_candidates))
    if selected is not None:
        reasons.append("point_in_time_contract_candidate_selected")
    return _dedupe(reasons)


def _candidate_filter_reason_summary(scored_candidates: Sequence[Mapping[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for candidate in scored_candidates:
        for reason in candidate.get("hard_filter_fail_reason_codes") or []:
            reasons.append(str(reason))
    return reasons


def _preferred_dte_range(holding_minutes: float) -> tuple[int, int]:
    if holding_minutes <= 15:
        return (3, 7)
    if holding_minutes <= 60:
        return (7, 14)
    if holding_minutes <= 390:
        return (7, 21)
    return (21, 45)


def _target_dte(holding_minutes: float) -> int:
    if holding_minutes <= 15:
        return 3
    if holding_minutes <= 60:
        return 7
    if holding_minutes <= 390:
        return 14
    return 30


def _target_delta(handoff: Mapping[str, Any], event: Mapping[str, Any]) -> float:
    path_quality = _score(handoff, "path_quality_score", default=0.5)
    event_gap = _score(event, "4_event_gap_risk_score_390min", default=0.0)
    return _clip01(0.40 + 0.15 * path_quality + 0.10 * event_gap)


def _target_range_ok(required_right: str, strike: float | None, handoff: Mapping[str, Any]) -> bool:
    if strike is None:
        return True
    entry = _first_float(handoff, "expected_entry_price", "entry_price_assumption")
    target_low = _first_float(handoff, "target_price_low")
    target_high = _first_float(handoff, "target_price_high", "expected_target_price")
    if required_right == "call" and entry is not None and target_high is not None and target_high > entry:
        return strike <= target_high
    if required_right == "put" and entry is not None and target_low is not None and target_low < entry:
        return strike >= target_low
    return True


def _iv_rank_ceiling(market: Mapping[str, Any], event: Mapping[str, Any], policy: Mapping[str, Any]) -> float:
    explicit = _first_float(policy, "iv_rank_ceiling", "max_iv_rank")
    if explicit is not None:
        return _clip01(explicit)
    market_stress = _score(market, "1_market_risk_stress_score", default=0.25)
    event_gap = _score(event, "4_event_gap_risk_score_390min", default=0.0)
    return _clip01(0.65 + 0.15 * max(market_stress, event_gap))


def _normalize_right(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"c", "call"}:
        return "call"
    if text in {"p", "put"}:
        return "put"
    return "none"


def _triangular_fit(value: float, target: float, half_width: float) -> float:
    if half_width <= 0:
        return 0.0
    return _clip01(1.0 - abs(value - target) / half_width)


def _replay_context(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "option_chain_snapshot_ref": row.get("option_chain_snapshot_ref") or row.get("option_chain_snapshot_id"),
        "option_quote_available_time": row.get("option_quote_available_time") or row.get("option_chain_available_time"),
        "underlying_quote_snapshot_ref": row.get("underlying_quote_snapshot_ref") or row.get("underlying_quote_snapshot_id"),
        "underlying_reference_price": row.get("underlying_reference_price"),
    }


def _pending_option_context(row: Mapping[str, Any]) -> dict[str, Any]:
    pending_orders = row.get("pending_option_orders") or []
    if isinstance(pending_orders, str):
        pending_orders = _coerce_payload(pending_orders)
    if isinstance(pending_orders, Mapping):
        pending_orders = [pending_orders]
    pending_premium = _first_float(row, "pending_option_premium_exposure") or 0.0
    pending_fill_probability = _first_float(row, "pending_option_fill_probability_estimate")
    if pending_fill_probability is None:
        pending_fill_probability = 1.0 if pending_orders or pending_premium > 0 else 0.0
    has_pending = bool(pending_orders) or pending_premium * pending_fill_probability > 0
    return {
        "has_pending_option_exposure": has_pending,
        "pending_option_order_count": len(pending_orders) if isinstance(pending_orders, Sequence) else 0,
        "pending_option_premium_exposure": pending_premium,
        "pending_option_fill_probability_estimate": pending_fill_probability,
        "pending_option_cancellable_state": row.get("pending_option_cancellable_state"),
    }


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "adjusted"}


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("underlying_action_plan", "layer_8_underlying_handoff", "market_context_state", "event_context_vector", "option_expression_policy"):
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


def _first_float(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return value
    return None


def _score(mapping: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return _clip01(value)
    return _clip01(default)


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


def _clip01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


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


def _suffix(horizon: str) -> str:
    return horizon


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden Layer 8 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

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
    candidates = _candidate_rows(row)

    direction = _underlying_direction(underlying_plan, handoff)
    expression_type, option_right = _expression_type(direction, underlying_plan, policy)
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
    reason_codes = _reason_codes(expression_type, selected, dominant, candidates, option_right, policy)
    resolved_payload = {
        "8_resolved_expression_type": expression_type,
        "8_resolved_option_right": option_right,
        "8_resolved_dominant_horizon": dominant_horizon,
        "8_resolved_contract_ref": None if selected is None else selected["contract_ref"],
        "8_resolved_expression_confidence_score": dominant["expression_confidence_score"],
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
        **score_payload,
        **resolved_payload,
        "expression_vector": {**score_payload, **resolved_payload},
        "option_expression_plan": {
            "selected_expression_type": expression_type,
            "selected_option_right": option_right,
            "dominant_horizon": dominant_horizon,
            "selected_contract": _selected_contract_payload(selected),
            "contract_constraints": _contract_constraints(option_right, handoff, policy),
            "premium_risk_plan": _premium_risk_plan(selected, handoff, dominant),
            "underlying_thesis_ref": row.get("underlying_action_plan_ref") or underlying_plan.get("underlying_action_plan_ref"),
            "underlying_path_assumptions": handoff,
            "reason_codes": reason_codes,
            "diagnostics": {
                "candidate_count": len(candidates),
                "eligible_candidate_count": len(eligible_candidates),
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


def _expression_type(direction: str, underlying_plan: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[str, str]:
    if str(policy.get("option_expression_allowed") or policy.get("allow_option_expression") or "true").lower() in {"false", "0", "no", "blocked"}:
        return "no_option_expression", "none"
    action_type = str(underlying_plan.get("planned_underlying_action_type") or "").lower()
    if direction == "bullish" and action_type not in {"maintain", "no_trade"}:
        return "long_call", "call"
    if direction == "bearish" and action_type != "maintain":
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
    max_spread_pct = _score(policy, "max_option_spread_pct", default=0.18)
    dte = _first_float(candidate, "dte", "days_to_expiration") or 0.0
    delta = _first_float(candidate, "delta") or 0.0
    theta = abs(_first_float(candidate, "theta") or 0.0)
    vega = abs(_first_float(candidate, "vega") or 0.0)
    iv_rank = _score(candidate, "iv_rank", "implied_volatility_rank", default=0.50)
    volume = _first_float(candidate, "volume", "day_volume") or 0.0
    open_interest = _first_float(candidate, "open_interest") or 0.0
    target_dte = _target_dte(float(handoff.get("expected_holding_time_minutes") or 390.0))
    dte_fit = _triangular_fit(dte, target_dte, max(target_dte * 1.25, 3.0))
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
    eligible = right == required_right and bid > 0 and ask > 0 and mid > 0 and spread_pct <= max_spread_pct and dte > 0
    return {
        "contract_ref": str(candidate.get("contract_ref") or candidate.get("option_contract_ref") or candidate.get("symbol") or "").strip() or _stable_id("contract", right, dte, delta, mid),
        "option_right": right,
        "expiration": candidate.get("expiration"),
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
        "spread_pct": round(spread_pct, 6),
        "dte_fit_score": round(dte_fit, 6),
        "liquidity_fit_score": round(liquidity_fit, 6),
        "iv_fit_score": round(iv_fit, 6),
        "greek_fit_score": round(greek_fit, 6),
        "theta_risk_score": round(theta_risk, 6),
        "fill_quality_score": round(fill_quality, 6),
        "reward_risk_score": round(reward_risk, 6),
        "contract_fit_score": round(contract_fit if eligible else contract_fit * 0.25, 6),
        "eligible": eligible,
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
    keys = ("contract_ref", "option_right", "expiration", "dte", "delta", "gamma", "theta", "vega", "iv", "iv_rank", "bid_price", "ask_price", "mid_price", "spread_pct")
    return {key: selected.get(key) for key in keys}


def _contract_constraints(option_right: str, handoff: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    holding = float(handoff.get("expected_holding_time_minutes") or 390.0)
    target_dte = _target_dte(holding)
    target_delta = _target_delta(handoff, {})
    return {
        "allowed_option_right": option_right,
        "target_dte": target_dte if option_right != "none" else None,
        "min_dte": max(1, int(target_dte * 0.35)) if option_right != "none" else None,
        "max_dte": int(target_dte * 2.25) if option_right != "none" else None,
        "target_abs_delta": target_delta if option_right != "none" else None,
        "min_abs_delta": 0.25 if option_right != "none" else None,
        "max_abs_delta": 0.75 if option_right != "none" else None,
        "max_option_spread_pct": _score(policy, "max_option_spread_pct", default=0.18),
        "iv_rank_ceiling": _iv_rank_ceiling({}, {}, policy) if option_right != "none" else None,
        "theta_decay_tolerance": "intraday_or_defined_risk_only" if holding <= 390 else "review_required",
    }


def _premium_risk_plan(selected: Mapping[str, Any] | None, handoff: Mapping[str, Any], dominant: Mapping[str, Any]) -> dict[str, Any]:
    if selected is None:
        return {
            "max_premium_at_risk_pct": 0.0,
            "expected_premium_reward_risk_score": 0.0,
            "time_stop_minutes": handoff.get("expected_holding_time_minutes"),
            "risk_plan_reason_codes": ["no_option_expression_selected"],
        }
    return {
        "max_premium_at_risk_pct": 1.0,
        "expected_premium_reward_risk_score": dominant["reward_risk_score"],
        "theta_risk_score": dominant["theta_risk_score"],
        "time_stop_minutes": handoff.get("expected_holding_time_minutes"),
        "risk_plan_reason_codes": ["defined_premium_risk", "offline_option_expression_only"],
    }


def _reason_codes(expression_type: str, selected: Mapping[str, Any] | None, dominant: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], option_right: str, policy: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if expression_type == "no_option_expression":
        reasons.append("no_option_expression_selected")
    else:
        reasons.append(f"{expression_type}_selected")
    if selected is None and option_right != "none":
        reasons.append("no_eligible_option_contract_candidate")
    if not candidates:
        reasons.append("missing_option_chain_candidates")
    if dominant.get("theta_risk_score", 0.0) >= 0.65:
        reasons.append("theta_risk_pressure")
    if dominant.get("iv_fit_score", 0.0) <= 0.35 and expression_type != "no_option_expression":
        reasons.append("iv_fit_downgrade")
    if str(policy.get("option_expression_allowed") or policy.get("allow_option_expression") or "true").lower() in {"false", "0", "no", "blocked"}:
        reasons.append("option_expression_policy_blocked")
    if selected is not None:
        reasons.append("point_in_time_contract_candidate_selected")
    return _dedupe(reasons)


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

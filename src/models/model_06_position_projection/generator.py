"""Deterministic PositionProjectionModel V1 scaffold.

Layer 6 maps the final adjusted ``alpha_confidence_vector`` plus point-in-time
current/pending exposure, friction, risk-budget, and policy context into a
``position_projection_vector``. It projects target position state only; it does
not emit buy/sell/hold/open/close/reverse, instrument selection, broker routing,
or option-contract fields.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 6 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    alpha = _payload(row, "alpha_confidence_vector")
    current = _payload(row, "current_position_state")
    pending = _payload(row, "pending_position_state")
    friction = _payload(row, "position_level_friction")
    portfolio = _payload(row, "portfolio_exposure_state")
    risk = _payload(row, "risk_budget_state")
    policy = _payload(row, "policy_gate_state")

    effective_exposure = _effective_exposure(current, pending)
    payload: dict[str, Any] = {}
    horizon_details: dict[str, dict[str, Any]] = {}
    for horizon in HORIZONS:
        detail = _horizon_projection(horizon, alpha, effective_exposure, friction, portfolio, risk, policy)
        horizon_details[horizon] = detail
        suffix = _suffix(horizon)
        payload.update(
            {
                f"6_target_position_bias_score_{suffix}": detail["target_position_bias"],
                f"6_target_exposure_score_{suffix}": detail["target_exposure"],
                f"6_current_position_alignment_score_{suffix}": detail["current_position_alignment"],
                f"6_position_gap_score_{suffix}": detail["position_gap"],
                f"6_position_gap_magnitude_score_{suffix}": detail["position_gap_magnitude"],
                f"6_expected_position_utility_score_{suffix}": detail["expected_position_utility"],
                f"6_cost_to_adjust_position_score_{suffix}": detail["cost_to_adjust_position"],
                f"6_risk_budget_fit_score_{suffix}": detail["risk_budget_fit"],
                f"6_position_state_stability_score_{suffix}": detail["position_state_stability"],
                f"6_projection_confidence_score_{suffix}": detail["projection_confidence"],
            }
        )

    resolved = _resolve_horizon(horizon_details)
    payload.update(resolved)
    ref = _stable_id("ppv", target_candidate_id, available_time, model_version)
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "alpha_confidence_vector_ref": row.get("alpha_confidence_vector_ref"),
        "current_position_state_ref": row.get("current_position_state_ref"),
        "pending_position_state_ref": row.get("pending_position_state_ref"),
        "position_projection_vector_ref": ref,
        **payload,
        "position_projection_vector": payload,
        "position_projection_diagnostics": {
            "effective_current_exposure_score": effective_exposure["effective_current_exposure"],
            "current_position_exposure_score": effective_exposure["current_position_exposure"],
            "pending_exposure_size": effective_exposure["pending_exposure_size"],
            "pending_order_fill_probability_estimate": effective_exposure["pending_fill_probability"],
            "horizon_projections": horizon_details,
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _effective_exposure(current: Mapping[str, Any], pending: Mapping[str, Any]) -> dict[str, float]:
    current_exposure = _signed(current, "current_position_exposure", "current_position_exposure_score", "exposure_score")
    pending_size = _signed(pending, "pending_exposure_size", "pending_exposure_score")
    fill_probability = _score(pending, "pending_order_fill_probability_estimate", "pending_fill_probability_estimate", "fill_probability_estimate", default=0.0)
    effective = _clip_signed(current_exposure + pending_size * fill_probability)
    return {
        "current_position_exposure": round(current_exposure, 6),
        "pending_exposure_size": round(pending_size, 6),
        "pending_fill_probability": round(fill_probability, 6),
        "effective_current_exposure": round(effective, 6),
    }


def _horizon_projection(
    horizon: str,
    alpha: Mapping[str, Any],
    exposure: Mapping[str, float],
    friction: Mapping[str, Any],
    portfolio: Mapping[str, Any],
    risk: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    suffix = _suffix(horizon)
    direction = _signed(alpha, f"5_alpha_direction_score_{suffix}")
    strength = _score(alpha, f"5_alpha_strength_score_{suffix}", default=0.0)
    expected_return = _signed(alpha, f"5_expected_return_score_{suffix}")
    confidence = _score(alpha, f"5_alpha_confidence_score_{suffix}", default=0.0)
    reliability = _score(alpha, f"5_signal_reliability_score_{suffix}", default=0.0)
    path_quality = _score(alpha, f"5_path_quality_score_{suffix}", default=0.5)
    reversal = _score(alpha, f"5_reversal_risk_score_{suffix}", default=0.5)
    drawdown = _score(alpha, f"5_drawdown_risk_score_{suffix}", default=0.5)
    alpha_tradability = _score(alpha, f"5_alpha_tradability_score_{suffix}", default=0.0)
    risk_fit = _risk_budget_fit(portfolio, risk, policy)
    conversion = _clip01(0.25 * strength + 0.25 * confidence + 0.20 * reliability + 0.20 * path_quality + 0.10 * alpha_tradability)
    risk_penalty = _clip01(0.45 * reversal + 0.45 * drawdown + 0.10 * (1.0 - risk_fit))
    raw_target = _clip_signed(direction * conversion * (1.0 - 0.55 * risk_penalty))
    if _policy_blocks_new_exposure(policy):
        raw_target = 0.0
        risk_fit = min(risk_fit, 0.0)
    target_exposure = _apply_exposure_limits(raw_target, portfolio, risk)
    effective = float(exposure["effective_current_exposure"])
    gap = _clip_signed(target_exposure - effective)
    gap_magnitude = _clip01(abs(gap))
    cost = _cost_to_adjust(gap_magnitude, friction)
    utility = _clip_signed(abs(expected_return) * confidence * path_quality - cost * gap_magnitude - (1.0 - risk_fit) * 0.25)
    alignment = _clip01(1.0 - gap_magnitude)
    stability = _clip01(0.35 * path_quality + 0.25 * reliability + 0.20 * alignment + 0.20 * (1.0 - max(reversal, drawdown)))
    projection_confidence = _clip01(0.35 * confidence + 0.25 * reliability + 0.20 * stability + 0.20 * risk_fit)
    reason_codes = []
    if gap_magnitude < 0.025:
        reason_codes.append("current_effective_exposure_already_aligned")
    if cost >= 0.65:
        reason_codes.append("adjustment_cost_pressure")
    if risk_fit <= 0.25:
        reason_codes.append("risk_budget_compression")
    if not reason_codes:
        reason_codes.append("alpha_to_position_projection")
    return {
        "target_position_bias": round(_clip_signed(direction * conversion), 6),
        "target_exposure": round(target_exposure, 6),
        "current_position_alignment": round(alignment, 6),
        "position_gap": round(gap, 6),
        "position_gap_magnitude": round(gap_magnitude, 6),
        "expected_position_utility": round(utility, 6),
        "cost_to_adjust_position": round(cost, 6),
        "risk_budget_fit": round(risk_fit, 6),
        "position_state_stability": round(stability, 6),
        "projection_confidence": round(projection_confidence, 6),
        "reason_codes": reason_codes,
    }


def _risk_budget_fit(portfolio: Mapping[str, Any], risk: Mapping[str, Any], policy: Mapping[str, Any]) -> float:
    if str(policy.get("kill_switch_state") or risk.get("kill_switch_state") or "").lower() in {"active", "on", "true", "halt"}:
        return 0.0
    available = _score(risk, "risk_budget_available_score", "risk_budget_fit_score", default=0.75)
    drawdown_state = _score(risk, "drawdown_state", "drawdown_pressure_score", default=0.25)
    concentration = _score(portfolio, "correlation_concentration_score", "concentration_score", default=0.25)
    volatility = _score(risk, "volatility_budget_state", "volatility_budget_pressure_score", default=0.25)
    return _clip01(0.55 * available + 0.15 * (1.0 - drawdown_state) + 0.15 * (1.0 - concentration) + 0.15 * (1.0 - volatility))


def _cost_to_adjust(gap_magnitude: float, friction: Mapping[str, Any]) -> float:
    spread = _score(friction, "spread_cost_estimate", default=0.02)
    slippage = _score(friction, "slippage_cost_estimate", default=0.03)
    fee = _score(friction, "fee_cost_estimate", default=0.01)
    turnover = _score(friction, "turnover_cost_estimate", default=0.02)
    capacity = _score(friction, "liquidity_capacity_score", default=0.80)
    raw_cost = 0.30 * spread + 0.30 * slippage + 0.10 * fee + 0.20 * turnover + 0.10 * (1.0 - capacity)
    return _clip01(raw_cost * max(gap_magnitude, 0.0) * 2.0)


def _apply_exposure_limits(target: float, portfolio: Mapping[str, Any], risk: Mapping[str, Any]) -> float:
    single_limit = _score(risk, "single_name_exposure_limit", "max_single_name_exposure_score", default=1.0)
    sector_limit = _score(portfolio, "sector_exposure_limit", default=1.0)
    available = _score(risk, "risk_budget_available_score", default=0.75)
    limit = max(0.0, min(1.0, single_limit, sector_limit, available if available < 0.20 else 1.0))
    return _clip_signed(max(-limit, min(limit, target)))


def _policy_blocks_new_exposure(policy: Mapping[str, Any]) -> bool:
    value = str(policy.get("new_exposure_allowed") or policy.get("allow_new_exposure") or "true").lower()
    return value in {"false", "0", "no", "blocked"}


def _resolve_horizon(details: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        details.items(),
        key=lambda item: (
            float(item[1]["projection_confidence"]) * max(float(item[1]["risk_budget_fit"]), 0.01)
            + float(item[1]["expected_position_utility"]) * 0.10
            - float(item[1]["cost_to_adjust_position"]) * 0.05
        ),
        reverse=True,
    )
    dominant_horizon, dominant = ranked[0]
    signs = {_sign(float(detail["target_exposure"])) for detail in details.values() if abs(float(detail["target_exposure"])) >= 0.025}
    conflict = "direction_conflict" if len(signs) > 1 else "aligned" if signs else "flat_or_no_projection"
    confidence = float(dominant["projection_confidence"])
    if conflict == "direction_conflict":
        confidence = max(0.0, confidence - 0.25)
    reason_codes = [f"selected_{dominant_horizon}_highest_projection_score"]
    if conflict == "direction_conflict":
        reason_codes.append("horizon_direction_conflict")
    return {
        "6_dominant_projection_horizon": dominant_horizon,
        "6_horizon_conflict_state": conflict,
        "6_resolved_target_exposure_score": round(float(dominant["target_exposure"]), 6),
        "6_resolved_position_gap_score": round(float(dominant["position_gap"]), 6),
        "6_projection_resolution_confidence_score": round(confidence, 6),
        "6_horizon_resolution_reason_codes": reason_codes,
    }


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in (
        "alpha_confidence_vector",
        "current_position_state",
        "pending_position_state",
        "position_level_friction",
        "portfolio_exposure_state",
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


def _score(mapping: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return _clip01(value)
    return _clip01(default)


def _signed(mapping: Mapping[str, Any], *keys: str) -> float:
    for key in keys:
        value = _safe_float(mapping.get(key))
        if value is not None:
            return _clip_signed(value)
    return 0.0


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


def _clip_signed(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(-1.0, min(1.0, float(value)))


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


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


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden Layer 6 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

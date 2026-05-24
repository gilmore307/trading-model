"""Deterministic DynamicRiskPolicyModel scaffold.

Layer 6 converts minute-level market, systemic event pressure, and replayed
portfolio/account capacity into dynamic_risk_policy_state. It may also emit
target- or position-conditioned policy rows when alpha or position context is
present. It does not enforce hard order limits and does not grant broker
permission.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 6 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("policy_scope") or ""), str(row.get("policy_scope_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    policy_scope, policy_scope_id, target_candidate_id = _policy_identity(row)

    market = _payload(row, "market_context_state")
    event = _payload(row, "systemic_event_risk_state")
    alpha = _payload(row, "alpha_confidence_vector")
    portfolio = _payload(row, "portfolio_exposure_state")
    account = _payload(row, "account_capacity_state")

    payload: dict[str, Any] = {}
    horizon_details: dict[str, dict[str, Any]] = {}
    for horizon in HORIZONS:
        detail = _horizon_policy(horizon, market, event, alpha, portfolio, account)
        horizon_details[horizon] = detail
        suffix = _suffix(horizon)
        payload.update(
            {
                f"6_dynamic_risk_budget_score_{suffix}": detail["dynamic_risk_budget"],
                f"6_premium_budget_score_{suffix}": detail["premium_budget"],
                f"6_new_exposure_permission_score_{suffix}": detail["new_exposure_permission"],
                f"6_market_stress_haircut_score_{suffix}": detail["market_stress_haircut"],
                f"6_systemic_event_haircut_score_{suffix}": detail["systemic_event_haircut"],
                f"6_portfolio_capacity_score_{suffix}": detail["portfolio_capacity"],
                f"6_policy_stability_score_{suffix}": detail["policy_stability"],
                f"6_risk_policy_confidence_score_{suffix}": detail["risk_policy_confidence"],
            }
        )

    resolved = _resolve_horizon(horizon_details)
    payload.update(resolved)
    ref = _stable_id("drp", policy_scope, policy_scope_id, available_time, model_version)
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "policy_scope": policy_scope,
        "policy_scope_id": policy_scope_id,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "market_context_state_ref": row.get("market_context_state_ref"),
        "alpha_confidence_vector_ref": row.get("alpha_confidence_vector_ref"),
        "portfolio_exposure_state_ref": row.get("portfolio_exposure_state_ref"),
        "dynamic_risk_policy_state_ref": ref,
        **payload,
        "dynamic_risk_policy_state": payload,
        "dynamic_risk_policy_diagnostics": {
            "horizon_policy": horizon_details,
            "global_market_driven": True,
            "minute_level_training_row": policy_scope == "global",
            "hard_order_limits_enforced_here": False,
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _horizon_policy(horizon: str, market: Mapping[str, Any], event: Mapping[str, Any], alpha: Mapping[str, Any], portfolio: Mapping[str, Any], account: Mapping[str, Any]) -> dict[str, Any]:
    suffix = _suffix(horizon)
    stress = _score(market, f"1_market_risk_stress_score_{suffix}", "1_market_risk_stress_score", default=0.25)
    liquidity = _score(market, f"1_market_liquidity_support_score_{suffix}", "1_market_liquidity_support_score", default=0.70)
    transition = _score(market, f"1_transition_risk_score_{suffix}", "1_transition_risk_score", default=0.25)
    systemic = _score(event, f"systemic_event_risk_score_{suffix}", "systemic_event_risk_score", default=0.20)
    alpha_quality = _score(alpha, f"5_alpha_confidence_score_{suffix}", "5_alpha_confidence_score_1W", default=0.50)
    path_quality = _score(alpha, f"5_path_quality_score_{suffix}", "5_path_quality_score_1W", default=0.50)
    drawdown = _score(account, "drawdown_pressure_score", default=0.20)
    cash = _score(account, "cash_capacity_score", "premium_capacity_score", default=0.70)
    concentration = _score(portfolio, "correlation_concentration_score", "concentration_score", default=0.25)
    gross_capacity = _score(portfolio, "gross_exposure_capacity_score", default=0.70)

    market_haircut = _clip01(0.55 * stress + 0.30 * transition + 0.15 * (1.0 - liquidity))
    event_haircut = _clip01(systemic)
    portfolio_capacity = _clip01(0.45 * gross_capacity + 0.35 * (1.0 - concentration) + 0.20 * (1.0 - drawdown))
    alpha_support = _clip01(0.60 * alpha_quality + 0.40 * path_quality)
    risk_budget = _clip01(portfolio_capacity * (1.0 - 0.55 * market_haircut) * (1.0 - 0.45 * event_haircut) * (0.55 + 0.45 * alpha_support))
    premium_budget = _clip01(cash * risk_budget * (0.70 + 0.30 * liquidity))
    permission = _clip01(0.50 * risk_budget + 0.30 * premium_budget + 0.20 * alpha_support)
    stability = _clip01(1.0 - max(market_haircut, event_haircut, drawdown))
    confidence = _clip01(0.35 * alpha_support + 0.25 * liquidity + 0.20 * portfolio_capacity + 0.20 * stability)
    reasons = []
    if market_haircut >= 0.60:
        reasons.append("market_stress_haircut")
    if event_haircut >= 0.60:
        reasons.append("systemic_event_haircut")
    if portfolio_capacity <= 0.35:
        reasons.append("portfolio_capacity_compressed")
    if not reasons:
        reasons.append("global_market_policy_budget_available")
    return {
        "dynamic_risk_budget": round(risk_budget, 6),
        "premium_budget": round(premium_budget, 6),
        "new_exposure_permission": round(permission, 6),
        "market_stress_haircut": round(market_haircut, 6),
        "systemic_event_haircut": round(event_haircut, 6),
        "portfolio_capacity": round(portfolio_capacity, 6),
        "policy_stability": round(stability, 6),
        "risk_policy_confidence": round(confidence, 6),
        "reason_codes": reasons,
    }


def _resolve_horizon(details: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ranked = sorted(details.items(), key=lambda item: float(item[1]["risk_policy_confidence"]) + 0.25 * float(item[1]["policy_stability"]), reverse=True)
    horizon, detail = ranked[0]
    reasons = [f"selected_{horizon}_highest_policy_confidence", *[str(reason) for reason in detail["reason_codes"]]]
    return {
        "6_resolved_dynamic_risk_budget_score": round(float(detail["dynamic_risk_budget"]), 6),
        "6_resolved_premium_budget_score": round(float(detail["premium_budget"]), 6),
        "6_resolved_new_exposure_permission_score": round(float(detail["new_exposure_permission"]), 6),
        "6_resolved_risk_policy_horizon": horizon,
        "6_risk_policy_reason_codes": sorted(set(reasons)),
    }


def _payload(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(loaded) if isinstance(loaded, Mapping) else {}
    return {}


def _policy_identity(row: Mapping[str, Any]) -> tuple[str, str, str | None]:
    target_candidate_id = str(row.get("target_candidate_id") or "").strip() or None
    position_id = str(row.get("position_id") or "").strip() or None
    requested_scope = str(row.get("policy_scope") or "").strip()
    if requested_scope:
        policy_scope = requested_scope
    elif target_candidate_id:
        policy_scope = "target_candidate"
    elif position_id:
        policy_scope = "active_position"
    else:
        policy_scope = "global"
    if policy_scope not in {"global", "target_candidate", "active_position"}:
        raise ValueError(f"unsupported Layer 6 policy_scope: {policy_scope}")
    if policy_scope == "target_candidate":
        if not target_candidate_id:
            raise ValueError("target_candidate_id is required for target_candidate policy_scope")
        return policy_scope, target_candidate_id, target_candidate_id
    if policy_scope == "active_position":
        if not position_id:
            raise ValueError("position_id is required for active_position policy_scope")
        return policy_scope, position_id, target_candidate_id
    return policy_scope, "global", target_candidate_id


def _score(payload: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in payload and payload[key] is not None:
            try:
                return _clip01(float(payload[key]))
            except (TypeError, ValueError):
                continue
    return _clip01(default)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _suffix(horizon: str) -> str:
    return horizon


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time"))


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("available_time is required")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    normalized["available_time"] = _iso(_row_time(row))
    if normalized.get("tradeable_time"):
        normalized["tradeable_time"] = _iso(_parse_time(normalized["tradeable_time"]))
    policy_scope, policy_scope_id, target_candidate_id = _policy_identity(normalized)
    normalized["policy_scope"] = policy_scope
    normalized["policy_scope_id"] = policy_scope_id
    if target_candidate_id:
        normalized["target_candidate_id"] = target_candidate_id
    return normalized


def _validate_no_forbidden_output(value: Any, *, path: str = "row") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden Layer 6 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, path=f"{path}[{index}]")

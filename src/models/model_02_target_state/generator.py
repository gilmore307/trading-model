"""TargetStateModel deterministic pilot generator."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_MODEL_FACING_FIELDS, HORIZONS, MODEL_ID, MODEL_STEP, MODEL_VERSION

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M02 target state input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")
    target_state_ref = _stable_id("tcs", target_candidate_id, available_time, model_version)
    background = _payload(row, "background_context_state")
    features = _payload(row, "anonymous_target_feature_vector", "target_feature_vector", "target_features")
    horizon_payloads = {horizon: _horizon_payload(row, background, features, horizon) for horizon in HORIZONS}
    scores = _score_payload(horizon_payloads)
    state_payload = {
        "score_payload": scores,
        "anonymous_target_feature_vector": _sanitize_model_facing_payload(features),
        "background_context_ref": row.get("background_context_state_ref"),
        "identity_policy": "target_candidate_id_only_no_raw_symbol_or_company_in_model_payload",
    }
    _validate_model_facing_payload(state_payload)
    output = {
        "available_time": available_time,
        "tradeable_time": _iso(_parse_time(row.get("tradeable_time") or available_time)),
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": row.get("background_context_state_ref"),
        "target_context_state_ref": target_state_ref,
        **scores,
        "target_context_state": state_payload,
        "target_state_diagnostics": {
            "audit_symbol_present_outside_model_payload": bool(row.get("symbol") or row.get("routing_symbol")),
            "model_payload_identity_leakage_check": "passed",
            "evidence_count": _evidence_count(features),
        },
    }
    return output


def _horizon_payload(row: Mapping[str, Any], background: Mapping[str, Any], features: Mapping[str, Any], horizon: str) -> dict[str, float]:
    suffix = horizon
    direction = _signed(features, f"target_return_{suffix}", f"target_direction_score_{suffix}", f"2_target_direction_score_{suffix}", default=_signed(row, f"target_return_{suffix}", "target_direction_score", default=0.0))
    trend_quality = _score(features, f"target_trend_quality_score_{suffix}", "target_trend_quality_score", default=0.55 + 0.35 * abs(direction))
    liquidity = _score(features, "target_liquidity_tradability_score", "liquidity_tradability_score", "liquidity_score", default=0.70)
    volatility = _score(features, f"target_volatility_pressure_score_{suffix}", "target_volatility_pressure_score", "volatility_pressure_score", default=0.25)
    transition_risk = _score(features, f"target_transition_risk_score_{suffix}", "target_transition_risk_score", default=0.25)
    market_stress = _score(background, f"1_market_risk_stress_score_{suffix}", "1_market_risk_stress_score", default=0.25)
    market_liquidity = _score(background, f"1_market_liquidity_support_score_{suffix}", "1_market_liquidity_support_score", default=0.70)
    support_quality = _clip01(_average([1.0 - market_stress, market_liquidity, trend_quality]))
    path_stability = _clip01(_average([1.0 - volatility, 1.0 - transition_risk, trend_quality]))
    noise = _clip01(_average([volatility, transition_risk, 1.0 - liquidity]))
    tradability = _clip01(_average([trend_quality, path_stability, liquidity, support_quality, 1.0 - noise]))
    return {
        "target_direction_score": direction,
        "target_trend_quality_score": trend_quality,
        "target_path_stability_score": path_stability,
        "target_noise_score": noise,
        "target_transition_risk_score": transition_risk,
        "context_support_quality_score": support_quality,
        "tradability_score": tradability,
    }


def _score_payload(horizon_payloads: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for horizon, payload in horizon_payloads.items():
        for name, value in payload.items():
            output[f"2_{name}_{horizon}"] = round(value, 6)
    return output


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("background_context_state", "anonymous_target_feature_vector", "target_feature_vector", "target_features"):
        output[key] = _coerce_payload(output.get(key))
    return output


def _payload(row: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = _coerce_payload(row.get(key))
        if isinstance(value, Mapping) and value:
            return dict(value)
    return {}


def _sanitize_model_facing_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _sanitize_model_facing_payload(nested) for key, nested in value.items() if str(key).lower() not in FORBIDDEN_MODEL_FACING_FIELDS}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_model_facing_payload(nested) for nested in value]
    return value


def _validate_model_facing_payload(value: Any, path: str = "target_context_state") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in FORBIDDEN_MODEL_FACING_FIELDS:
                raise ValueError(f"forbidden M02 model-facing field at {path}.{key}: {key}")
            _validate_model_facing_payload(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_model_facing_payload(nested, f"{path}[{index}]")


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


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("snapshot_time"))


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        raise ValueError("available_time is required")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ET)
    return value.astimezone(ET).isoformat()


def _score(row: Mapping[str, Any], *keys: str, default: float) -> float:
    for key in keys:
        value = _safe_float(row.get(key))
        if value is not None:
            return _clip01(value)
    return _clip01(default)


def _signed(row: Mapping[str, Any], *keys: str, default: float) -> float:
    for key in keys:
        value = _safe_float(row.get(key))
        if value is not None:
            return _clip_signed(value)
    return _clip_signed(default)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _average(values: Iterable[float | None]) -> float:
    clean = [float(value) for value in values if value is not None]
    return sum(clean) / len(clean) if clean else 0.0


def _evidence_count(value: Any) -> int:
    if isinstance(value, Mapping):
        return sum(_evidence_count(nested) for nested in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return sum(_evidence_count(nested) for nested in value)
    return 1 if _safe_float(value) is not None else 0


def _clip01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _clip_signed(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(-1.0, min(1.0, float(value)))


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"

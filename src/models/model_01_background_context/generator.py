"""BackgroundContextModel deterministic pilot generator."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_STEP, MODEL_VERSION

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M01 background context input row is required")
    rows.sort(key=lambda row: _row_time(row))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    background_ref = _stable_id("bcs", available_time, model_version)
    horizon_payloads = {horizon: _horizon_payload(row, horizon) for horizon in HORIZONS}
    scores = _score_payload(horizon_payloads)
    quality = _average([payload["background_context_quality_score"] for payload in horizon_payloads.values()])
    output = {
        "available_time": available_time,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": background_ref,
        **scores,
        "1_market_risk_stress_score": scores["1_market_risk_stress_score_1W"],
        "1_market_liquidity_support_score": scores["1_market_liquidity_support_score_1W"],
        "1_background_context_quality_score": round(quality, 6),
        "background_context_state": {
            "score_payload": {
                **scores,
                "1_market_risk_stress_score": scores["1_market_risk_stress_score_1W"],
                "1_market_liquidity_support_score": scores["1_market_liquidity_support_score_1W"],
                "1_background_context_quality_score": round(quality, 6),
            },
            "market_context": _payload(row, "market_context_features", "market_features"),
            "sector_context": _payload(row, "sector_context_features", "sector_features"),
            "diagnostics": {
                "evidence_count": _evidence_count(row),
                "input_contract": "point_in_time_background_context_features",
                "no_target_or_action_fields": True,
            },
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _horizon_payload(row: Mapping[str, Any], horizon: str) -> dict[str, float]:
    suffix = horizon
    market_return = _signed(row, f"market_return_{suffix}", f"market_direction_score_{suffix}", "market_return", "market_direction_score", default=0.0)
    sector_direction = _signed(row, f"sector_relative_direction_score_{suffix}", "sector_relative_direction_score", default=market_return)
    trend_quality = _score(row, f"market_trend_quality_score_{suffix}", "market_trend_quality_score", default=_quality_from_direction(market_return))
    volatility = _score(row, f"market_volatility_pressure_score_{suffix}", "market_volatility_pressure_score", "volatility_pressure_score", default=0.25)
    liquidity = _score(row, f"market_liquidity_support_score_{suffix}", "market_liquidity_support_score", "liquidity_support_score", default=0.70)
    stress = _score(row, f"market_risk_stress_score_{suffix}", "market_risk_stress_score", "risk_stress_score", default=_clip01(0.45 * volatility + 0.35 * (1.0 - liquidity) + 0.20 * abs(min(market_return, 0.0))))
    breadth = _score(row, f"sector_breadth_score_{suffix}", "sector_breadth_score", "breadth_score", default=_clip01((sector_direction + 1.0) / 2.0))
    dispersion = _score(row, f"sector_dispersion_score_{suffix}", "sector_dispersion_score", "dispersion_score", default=0.25)
    data_quality = _score(row, "data_quality_score", "source_quality_score", default=0.80)
    coverage = _score(row, "coverage_score", "feature_coverage_score", default=min(_evidence_count(row) / 8.0, 1.0))
    context_quality = _clip01(_average([trend_quality, liquidity, 1.0 - stress, 1.0 - dispersion, data_quality, coverage]))
    return {
        "market_direction_score": _clip_signed(_average([market_return, sector_direction * 0.25])),
        "market_trend_quality_score": trend_quality,
        "market_risk_stress_score": stress,
        "market_liquidity_support_score": liquidity,
        "market_volatility_pressure_score": volatility,
        "sector_breadth_score": breadth,
        "sector_dispersion_score": dispersion,
        "background_context_quality_score": context_quality,
    }


def _score_payload(horizon_payloads: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for horizon, payload in horizon_payloads.items():
        suffix = horizon
        for name, value in payload.items():
            output[f"1_{name}_{suffix}"] = round(value, 6)
    return output


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("market_context_features", "market_features", "sector_context_features", "sector_features"):
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


def _quality_from_direction(value: float) -> float:
    return _clip01(0.45 + min(abs(value), 1.0) * 0.45)


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


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden M01 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

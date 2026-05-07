"""Deterministic AlphaConfidenceModel V1 scaffold.

Layer 5 converts reviewed Layer 1/2/3 state plus Layer 4 event context into the
final adjusted ``alpha_confidence_vector``. The scaffold keeps base alpha as a
diagnostic surface and emits only alpha-confidence fields, not position/action/
execution fields.
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
        raise ValueError("at least one Layer 5 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    market = _payload(row, "market_context_state")
    sector = _payload(row, "sector_context_state")
    target = _payload(row, "target_context_state") or _payload(row, "target_state_vector")
    event = _payload(row, "event_context_vector")
    quality = _payload(row, "quality_calibration_state")

    final_payload: dict[str, Any] = {}
    base_payload: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {"horizon_reason_codes": {}}
    for horizon in HORIZONS:
        suffix = _suffix(horizon)
        base = _base_alpha(horizon, market, sector, target)
        adjusted = _adjust_for_events(horizon, base, event)
        calibrated = _calibrate(horizon, adjusted, quality, market, sector, target, event)
        final_payload.update(
            {
                f"5_alpha_direction_score_{suffix}": calibrated["alpha_direction"],
                f"5_alpha_strength_score_{suffix}": calibrated["alpha_strength"],
                f"5_expected_return_score_{suffix}": calibrated["expected_return"],
                f"5_alpha_confidence_score_{suffix}": calibrated["alpha_confidence"],
                f"5_signal_reliability_score_{suffix}": calibrated["signal_reliability"],
                f"5_path_quality_score_{suffix}": calibrated["path_quality"],
                f"5_reversal_risk_score_{suffix}": calibrated["reversal_risk"],
                f"5_drawdown_risk_score_{suffix}": calibrated["drawdown_risk"],
                f"5_alpha_tradability_score_{suffix}": calibrated["alpha_tradability"],
            }
        )
        base_payload.update(
            {
                f"5_base_alpha_direction_score_{suffix}": base["direction"],
                f"5_base_alpha_strength_score_{suffix}": base["strength"],
                f"5_base_expected_return_score_{suffix}": base["expected_return"],
                f"5_base_path_quality_score_{suffix}": base["path_quality"],
                f"5_base_reversal_risk_score_{suffix}": base["reversal_risk"],
                f"5_base_drawdown_risk_score_{suffix}": base["drawdown_risk"],
                f"5_base_alpha_tradability_score_{suffix}": base["tradability"],
                f"5_market_adjusted_alpha_score_{suffix}": base["market_adjusted_alpha"],
                f"5_sector_adjusted_alpha_score_{suffix}": base["sector_adjusted_alpha"],
                f"5_target_state_lift_score_{suffix}": base["target_state_lift"],
                f"5_beta_dependency_score_{suffix}": base["beta_dependency"],
                f"5_event_direction_adjustment_score_{suffix}": adjusted["event_direction_adjustment"],
                f"5_event_strength_adjustment_score_{suffix}": adjusted["event_strength_adjustment"],
                f"5_event_risk_adjustment_score_{suffix}": adjusted["event_risk_adjustment"],
                f"5_event_override_mode_{suffix}": adjusted["event_override_mode"],
            }
        )
        diagnostics["horizon_reason_codes"][horizon] = calibrated["reason_codes"]

    ref = _stable_id("acv", target_candidate_id, available_time, model_version)
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "market_context_state_ref": row.get("market_context_state_ref"),
        "sector_context_state_ref": row.get("sector_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref") or row.get("target_state_vector_ref"),
        "event_context_vector_ref": row.get("event_context_vector_ref"),
        "alpha_confidence_vector_ref": ref,
        **final_payload,
        "alpha_confidence_vector": final_payload,
        "base_alpha_vector": base_payload,
        "alpha_confidence_diagnostics": diagnostics,
    }
    _validate_no_forbidden_output(output)
    return output


def _base_alpha(horizon: str, market: Mapping[str, Any], sector: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, float]:
    suffix = _suffix(horizon)
    target_direction = _signed(target, f"3_target_direction_score_{suffix}", "target_direction_score")
    trend_quality = _score(target, f"3_target_trend_quality_score_{suffix}", "target_trend_quality_score", default=0.5)
    path_stability = _score(target, f"3_target_path_stability_score_{suffix}", "target_path_stability_score", default=0.5)
    noise = _score(target, f"3_target_noise_score_{suffix}", "target_noise_score", default=0.35)
    transition_risk = _score(target, f"3_target_transition_risk_score_{suffix}", "target_transition_risk_score", default=0.35)
    target_tradability = _score(target, f"3_tradability_score_{suffix}", "3_target_liquidity_tradability_score", default=0.65)
    target_quality = _score(target, "3_state_quality_score", "target_state_quality_score", default=0.65)
    context_alignment = _signed(target, f"3_context_direction_alignment_score_{suffix}", "context_direction_alignment_score")
    context_support = _score(target, f"3_context_support_quality_score_{suffix}", "context_support_quality_score", default=0.5)
    market_risk = _score(market, "1_market_risk_stress_score", "market_risk_stress_score", default=0.35)
    market_liquidity = _score(market, "1_market_liquidity_support_score", "market_liquidity_support_score", default=0.65)
    sector_support = _score(sector, "2_sector_context_support_quality_score", f"2_context_support_quality_score_{suffix}", default=0.55)
    beta_dependency = _score(target, f"3_beta_dependency_score_{suffix}", "beta_dependency_score", default=0.35)

    raw_strength = abs(target_direction) * (0.35 + 0.25 * trend_quality + 0.20 * path_stability + 0.10 * context_support + 0.10 * sector_support)
    risk_penalty = 0.35 * transition_risk + 0.20 * noise + 0.20 * market_risk + 0.25 * beta_dependency
    strength = _clip01(raw_strength * (1.0 - 0.45 * risk_penalty) * target_quality)
    direction = _clip_signed(target_direction * (0.75 + 0.25 * max(context_alignment, 0.0)))
    expected_return = _clip_signed(direction * strength * (0.6 + 0.4 * (1.0 - beta_dependency)))
    path_quality = _clip01(0.35 * path_stability + 0.25 * trend_quality + 0.20 * (1.0 - noise) + 0.20 * market_liquidity)
    reversal_risk = _clip01(0.45 * transition_risk + 0.25 * noise + 0.20 * (1.0 - path_stability) + 0.10 * market_risk)
    drawdown_risk = _clip01(0.35 * market_risk + 0.25 * (1.0 - market_liquidity) + 0.20 * noise + 0.20 * transition_risk)
    tradability = _clip01(strength * 0.35 + path_quality * 0.30 + target_tradability * 0.25 + (1.0 - max(reversal_risk, drawdown_risk)) * 0.10)
    return {
        "direction": round(direction, 6),
        "strength": round(strength, 6),
        "expected_return": round(expected_return, 6),
        "path_quality": round(path_quality, 6),
        "reversal_risk": round(reversal_risk, 6),
        "drawdown_risk": round(drawdown_risk, 6),
        "tradability": round(tradability, 6),
        "market_adjusted_alpha": round(_clip_signed(expected_return * (1.0 - 0.5 * market_risk)), 6),
        "sector_adjusted_alpha": round(_clip_signed(expected_return * (0.65 + 0.35 * sector_support)), 6),
        "target_state_lift": round(_clip01(strength * (1.0 - beta_dependency)), 6),
        "beta_dependency": round(beta_dependency, 6),
    }


def _adjust_for_events(horizon: str, base: Mapping[str, float], event: Mapping[str, Any]) -> dict[str, Any]:
    suffix = _suffix(horizon)
    presence = _score(event, f"4_event_presence_score_{suffix}", default=0.0)
    intensity = _score(event, f"4_event_intensity_score_{suffix}", default=0.0)
    relevance = _score(event, f"4_event_target_relevance_score_{suffix}", default=0.0)
    event_quality = _score(event, f"4_event_context_quality_score_{suffix}", default=0.65)
    event_direction = _signed(event, f"4_event_direction_bias_score_{suffix}")
    alignment = _signed(event, f"4_event_context_alignment_score_{suffix}")
    uncertainty = _score(event, f"4_event_uncertainty_score_{suffix}", default=0.0)
    reversal = _score(event, f"4_event_reversal_risk_score_{suffix}", default=0.0)
    gap = _score(event, f"4_event_gap_risk_score_{suffix}", default=0.0)
    liquidity = _score(event, f"4_event_liquidity_disruption_score_{suffix}", default=0.0)
    event_weight = _clip01(presence * intensity * relevance * event_quality)
    override = bool(event_weight >= 0.55 and abs(event_direction) >= 0.65 and event_quality >= 0.70)
    direction_adjustment = event_direction * event_weight * (0.75 if override else 0.35)
    strength_adjustment = event_weight * (0.25 if event_direction * float(base["direction"]) >= 0 else -0.25)
    risk_adjustment = _clip01((uncertainty * 0.35 + reversal * 0.35 + gap * 0.20 + liquidity * 0.10) * max(presence, relevance))
    adjusted_direction = _clip_signed(float(base["direction"]) * (0.45 if override else 1.0) + direction_adjustment)
    adjusted_strength = _clip01(float(base["strength"]) + strength_adjustment - 0.25 * risk_adjustment)
    path_quality = _clip01(float(base["path_quality"]) + max(alignment, 0.0) * event_weight * 0.15 - risk_adjustment * 0.35)
    return {
        "direction": round(adjusted_direction, 6),
        "strength": round(adjusted_strength, 6),
        "expected_return": round(_clip_signed(adjusted_direction * adjusted_strength), 6),
        "path_quality": round(path_quality, 6),
        "reversal_risk": round(_clip01(float(base["reversal_risk"]) + reversal * event_weight * 0.40 + risk_adjustment * 0.20), 6),
        "drawdown_risk": round(_clip01(float(base["drawdown_risk"]) + gap * event_weight * 0.35 + liquidity * event_weight * 0.20), 6),
        "tradability": round(_clip01(float(base["tradability"]) + alignment * event_weight * 0.15 - risk_adjustment * 0.35), 6),
        "event_direction_adjustment": round(direction_adjustment, 6),
        "event_strength_adjustment": round(strength_adjustment, 6),
        "event_risk_adjustment": round(risk_adjustment, 6),
        "event_override_mode": override,
        "event_weight": round(event_weight, 6),
    }


def _calibrate(
    horizon: str,
    adjusted: Mapping[str, Any],
    quality: Mapping[str, Any],
    market: Mapping[str, Any],
    sector: Mapping[str, Any],
    target: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    suffix = _suffix(horizon)
    sample_support = _score(quality, "state_neighborhood_sample_count_score", "sample_support_score", default=0.55)
    stability = _score(quality, "state_neighborhood_outcome_stability", "walk_forward_reliability_score", default=0.55)
    ensemble = _score(quality, "model_ensemble_agreement_score", default=0.60)
    disagreement = _score(quality, "model_disagreement_score", default=0.25)
    ood = _score(quality, "out_of_distribution_score", default=0.20)
    data_quality = _score(quality, "data_quality_score", "feature_coverage_score", default=0.70)
    layer_quality = min(
        _score(market, "1_state_quality_score", default=0.75),
        _score(sector, "2_state_quality_score", default=0.75),
        _score(target, "3_state_quality_score", default=0.75),
        _score(event, f"4_event_context_quality_score_{suffix}", default=0.75),
        data_quality,
    )
    reliability = _clip01(0.25 * sample_support + 0.25 * stability + 0.20 * ensemble + 0.20 * layer_quality + 0.10 * (1.0 - max(disagreement, ood)))
    risk = max(float(adjusted["reversal_risk"]), float(adjusted["drawdown_risk"]))
    confidence = _clip01(float(adjusted["strength"]) * 0.40 + reliability * 0.35 + float(adjusted["path_quality"]) * 0.25)
    confidence = _clip01(confidence * (1.0 - 0.35 * risk) * (1.0 - 0.30 * ood))
    tradability = _clip01(float(adjusted["tradability"]) * 0.50 + confidence * 0.30 + float(adjusted["path_quality"]) * 0.20 - risk * 0.20)
    reason_codes = []
    if float(adjusted["strength"]) < 0.05:
        reason_codes.append("no_material_alpha_edge")
    if risk >= 0.65:
        reason_codes.append("path_risk_downgrade")
    if ood >= 0.65:
        reason_codes.append("out_of_distribution_downgrade")
    if adjusted.get("event_override_mode"):
        reason_codes.append("high_quality_event_override")
    if not reason_codes:
        reason_codes.append("state_alpha_calibrated")
    return {
        "alpha_direction": round(float(adjusted["direction"]), 6),
        "alpha_strength": round(float(adjusted["strength"]), 6),
        "expected_return": round(float(adjusted["expected_return"]), 6),
        "alpha_confidence": round(confidence, 6),
        "signal_reliability": round(reliability, 6),
        "path_quality": round(float(adjusted["path_quality"]), 6),
        "reversal_risk": round(float(adjusted["reversal_risk"]), 6),
        "drawdown_risk": round(float(adjusted["drawdown_risk"]), 6),
        "alpha_tradability": round(tradability, 6),
        "reason_codes": reason_codes,
    }


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("market_context_state", "sector_context_state", "target_context_state", "target_state_vector", "event_context_vector", "quality_calibration_state"):
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
                raise ValueError(f"forbidden Layer 5 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

"""EventStateModel deterministic pilot generator."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import (
    DEFAULT_ALLOWED_EFFECT_PROFILE,
    EVENT_DISTRIBUTION_EFFECT_CHANNELS,
    EVENT_IMPACT_CHANNELS,
    FORBIDDEN_OUTPUT_FIELDS,
    HORIZONS,
    MODEL_ID,
    MODEL_STEP,
    MODEL_VERSION,
)

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M03 event state input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")
    events = _event_rows(row)
    event_state_ref = _stable_id("esv", target_candidate_id, available_time, model_version)
    horizon_payloads = {horizon: _horizon_payload(row, events, horizon) for horizon in HORIZONS}
    scores = _score_payload(horizon_payloads)
    output = {
        "available_time": available_time,
        "tradeable_time": _iso(_parse_time(row.get("tradeable_time") or available_time)),
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": row.get("background_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref"),
        "event_state_vector_ref": event_state_ref,
        **scores,
        "event_state_vector": {
            "score_payload": scores,
            "impact_channel_scores": _impact_channel_vector(scores),
            "distribution_effect_scores": _distribution_effect_vector(scores),
            "allowed_effect_profiles": _event_effect_profile_refs(events),
            "frozen_event_contract_refs": _event_refs(events),
            "accepted_event_count": len(events),
            "event_parameter_mutation_allowed": False,
        },
        "event_state_diagnostics": {
            "accepted_event_count": len(events),
            "only_point_in_time_accepted_events": True,
            "no_standalone_event_alpha": True,
            "distribution_channel_permission_enforced": True,
            "directional_center_shift_default_forbidden": True,
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _horizon_payload(row: Mapping[str, Any], events: Sequence[Mapping[str, Any]], horizon: str) -> dict[str, float]:
    target = _payload(row, "target_context_state")
    target_direction = _signed(target, f"2_target_direction_score_{horizon}", "target_direction_score", default=0.0)
    if not events:
        return {
            "event_response_direction_score": 0.0,
            "event_response_strength_score": 0.0,
            "event_uncertainty_score": 0.0,
            "event_path_risk_score": 0.0,
            "event_entry_block_pressure_score": 0.0,
            "event_exposure_cap_pressure_score": 0.0,
            "event_strategy_disable_pressure_score": 0.0,
            "event_applicability_confidence_score": 0.0,
            **_empty_impact_channel_scores(),
            **_empty_distribution_effect_scores(),
        }
    intensities = [_score(event, "event_intensity_score", "intensity_score", default=0.35) for event in events]
    uncertainties = [_score(event, "uncertainty_score", "revision_risk_score", default=0.25) for event in events]
    direction_biases = [_directional_signal(event) for event in events]
    relevance = [_score(event, "target_relevance_score", "applicability_confidence_score", default=0.50) for event in events]
    risk_scores = [_score(event, "path_risk_score", "gap_risk_score", "event_path_risk_score", default=intensity * (0.45 + 0.35 * uncertainty)) for event, intensity, uncertainty in zip(events, intensities, uncertainties)]
    intensity = _average(intensities)
    uncertainty = _average(uncertainties)
    response_direction = _clip_signed(_average(direction_biases) * max(_average(relevance), 0.25))
    response_strength = _clip01(intensity * max(abs(response_direction), 0.35))
    path_risk = _clip01(_average(risk_scores))
    entry_block = _clip01(_average([path_risk, uncertainty, max(0.0, -response_direction * target_direction)]))
    exposure_cap = _clip01(_average([path_risk, uncertainty * 0.75]))
    disable = _clip01(max(0.0, path_risk - 0.70) + max(0.0, uncertainty - 0.80))
    applicability = _clip01(_average(relevance))
    return {
        "event_response_direction_score": response_direction,
        "event_response_strength_score": response_strength,
        "event_uncertainty_score": uncertainty,
        "event_path_risk_score": path_risk,
        "event_entry_block_pressure_score": entry_block,
        "event_exposure_cap_pressure_score": exposure_cap,
        "event_strategy_disable_pressure_score": disable,
        "event_applicability_confidence_score": applicability,
        **_impact_channel_scores(events),
        **_distribution_effect_scores(events),
    }


def _score_payload(horizon_payloads: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for horizon, payload in horizon_payloads.items():
        for name, value in payload.items():
            output[f"3_{name}_{horizon}"] = round(value, 6)
    return output


def _impact_channel_scores(events: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    return {
        "event_underlying_price_impact_score": _average_channel(
            events,
            "underlying_price",
            "underlying_price_impact_score",
            "underlying_impact_score",
        ),
        "event_option_price_impact_score": _average_channel(
            events,
            "option_price",
            "option_price_impact_score",
            "option_impact_score",
        ),
        "event_volatility_surface_impact_score": _average_channel(
            events,
            "volatility_surface",
            "volatility_surface_impact_score",
            "vol_surface_impact_score",
        ),
        "event_option_liquidity_spread_impact_score": _average_channel(
            events,
            "option_liquidity_spread",
            "option_liquidity_spread_impact_score",
            "liquidity_spread_impact_score",
        ),
        "event_expiry_gamma_flow_impact_score": _average_channel(
            events,
            "expiry_gamma_flow",
            "expiry_gamma_flow_impact_score",
            "gamma_flow_impact_score",
        ),
    }


def _empty_impact_channel_scores() -> dict[str, float]:
    return {f"event_{channel}_impact_score": 0.0 for channel in EVENT_IMPACT_CHANNELS}


def _empty_distribution_effect_scores() -> dict[str, float]:
    return {f"event_{channel}_score": 0.0 for channel in EVENT_DISTRIBUTION_EFFECT_CHANNELS}


def _average_channel(events: Sequence[Mapping[str, Any]], channel: str, *keys: str) -> float:
    values: list[float] = []
    for event in events:
        impact_channels = event.get("impact_channels")
        if isinstance(impact_channels, Mapping):
            value = _safe_float(impact_channels.get(channel))
            if value is not None:
                values.append(_clip01(value))
                continue
        for key in keys:
            value = _safe_float(event.get(key))
            if value is not None:
                values.append(_clip01(value))
                break
    return _clip01(_average(values))


def _impact_channel_vector(scores: Mapping[str, float]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for horizon in HORIZONS:
        output[horizon] = {
            channel: float(scores.get(f"3_event_{channel}_impact_score_{horizon}", 0.0))
            for channel in EVENT_IMPACT_CHANNELS
        }
    return output


def _distribution_effect_scores(events: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    mean_shifts: list[float] = []
    mode_shifts: list[float] = []
    contributions: list[float] = []
    variances: list[float] = []
    left_tails: list[float] = []
    right_tails: list[float] = []
    skews: list[float] = []
    confidence_discounts: list[float] = []
    gates: list[float] = []
    for event in events:
        permissions = _allowed_effect_profile(event)
        intensity = _score(event, "event_intensity_score", "intensity_score", default=0.35)
        uncertainty = _score(event, "uncertainty_score", "revision_risk_score", default=0.25)
        path_risk = _score(event, "path_risk_score", "gap_risk_score", "event_path_risk_score", default=intensity * (0.45 + 0.35 * uncertainty))
        relevance = _score(event, "target_relevance_score", "applicability_confidence_score", default=0.50)
        raw_direction = _signed(event, "event_response_direction_score", "direction_bias_score", "surprise_score", default=0.0)
        directional_signal = _directional_signal(event)
        if permissions["can_change_mean"]:
            mean_shifts.append(_signed_or_default(event, directional_signal * intensity * relevance, "mean_shift_score", "event_mean_shift_score"))
        if permissions["can_change_mode"]:
            mode_shifts.append(_signed_or_default(event, directional_signal * intensity * relevance, "mode_shift_score", "event_mode_shift_score"))
        if permissions["can_add_directional_contribution"]:
            contributions.append(_signed_or_default(event, directional_signal * intensity * relevance, "directional_contribution_score", "event_directional_contribution_score"))
        if permissions["can_change_variance"]:
            variances.append(_score(event, "variance_multiplier_score", "event_variance_multiplier_score", default=_clip01(0.55 * uncertainty + 0.45 * path_risk)))
        if permissions["can_change_left_tail"]:
            left_tails.append(_score(event, "left_tail_delta_score", "event_left_tail_delta_score", default=_clip01(path_risk * (1.0 + 0.35 * max(0.0, -raw_direction)))))
        if permissions["can_change_right_tail"]:
            right_tails.append(_score(event, "right_tail_delta_score", "event_right_tail_delta_score", default=_clip01(path_risk * (1.0 + 0.35 * max(0.0, raw_direction)))))
        if permissions["can_change_skew"]:
            skews.append(_signed_or_default(event, raw_direction * intensity * relevance, "skew_delta_score", "event_skew_delta_score"))
        if permissions["can_change_confidence"]:
            confidence_discounts.append(_score(event, "confidence_discount_score", "event_confidence_discount_score", default=_clip01(uncertainty * relevance)))
        if permissions["can_raise_gate"]:
            gates.append(_score(event, "gate_pressure_score", "event_gate_pressure_score", default=_clip01(_average([path_risk, uncertainty, intensity * 0.5]))))
    return {
        "event_mean_shift_score": _clip_signed(_average(mean_shifts)),
        "event_mode_shift_score": _clip_signed(_average(mode_shifts)),
        "event_directional_contribution_score": _clip_signed(_average(contributions)),
        "event_variance_multiplier_score": _clip01(_average(variances)),
        "event_left_tail_delta_score": _clip01(_average(left_tails)),
        "event_right_tail_delta_score": _clip01(_average(right_tails)),
        "event_skew_delta_score": _clip_signed(_average(skews)),
        "event_confidence_discount_score": _clip01(_average(confidence_discounts)),
        "event_gate_pressure_score": _clip01(_average(gates)),
    }


def _distribution_effect_vector(scores: Mapping[str, float]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for horizon in HORIZONS:
        output[horizon] = {
            channel: float(scores.get(f"3_event_{channel}_score_{horizon}", 0.0))
            for channel in EVENT_DISTRIBUTION_EFFECT_CHANNELS
        }
    return output


def _event_effect_profile_refs(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for event in events:
        profiles.append(
            {
                "event_ref": event.get("event_family_contract_ref") or event.get("canonical_event_id") or event.get("event_id"),
                "event_family_key": event.get("event_family_key") or event.get("mechanism_family") or event.get("normalized_event_type"),
                "projection_mode": event.get("projection_mode") or event.get("event_projection_mode") or "unreviewed_risk_shape_default",
                "allowed_effect_profile": _allowed_effect_profile(event),
            }
        )
    return profiles


def _directional_signal(event: Mapping[str, Any]) -> float:
    permissions = _allowed_effect_profile(event)
    if not (
        permissions["can_change_mean"]
        or permissions["can_change_mode"]
        or permissions["can_add_directional_contribution"]
    ):
        return 0.0
    return _signed(event, "event_response_direction_score", "direction_bias_score", "surprise_score", default=0.0)


def _allowed_effect_profile(event: Mapping[str, Any]) -> dict[str, bool]:
    profile = dict(DEFAULT_ALLOWED_EFFECT_PROFILE)
    raw_profile = (
        event.get("allowed_effect_profile")
        or event.get("distribution_effect_profile")
        or event.get("event_family_allowed_effect_profile")
        or {}
    )
    if isinstance(raw_profile, Mapping):
        for key in profile:
            if key in raw_profile:
                profile[key] = _bool_value(raw_profile.get(key))
        allowed_channels = raw_profile.get("allowed_channels") or raw_profile.get("channels")
        if isinstance(allowed_channels, Sequence) and not isinstance(allowed_channels, (str, bytes, bytearray)):
            allowed = {str(channel).strip() for channel in allowed_channels}
            profile = {key: _profile_key_to_channel(key) in allowed for key in profile}
    directional_flag = event.get("directional_effect_allowed") or event.get("directional_mean_shift_allowed")
    if directional_flag is not None and _bool_value(directional_flag):
        profile["can_change_mean"] = True
        profile["can_change_mode"] = True
        profile["can_add_directional_contribution"] = True
    return profile


def _profile_key_to_channel(key: str) -> str:
    return {
        "can_change_mean": "mean_shift",
        "can_change_mode": "mode_shift",
        "can_add_directional_contribution": "directional_contribution",
        "can_change_variance": "variance_multiplier",
        "can_change_left_tail": "left_tail_delta",
        "can_change_right_tail": "right_tail_delta",
        "can_change_skew": "skew_delta",
        "can_change_confidence": "confidence_discount",
        "can_raise_gate": "gate_pressure",
    }[key]


def _bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "allowed", "allow"}
    return bool(value)


def _signed_or_default(row: Mapping[str, Any], default: float, *keys: str) -> float:
    for key in keys:
        value = _safe_float(row.get(key))
        if value is not None:
            return _clip_signed(value)
    return _clip_signed(default)


def _event_rows(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    events = (
        row.get("accepted_event_contracts")
        or row.get("accepted_event_contexts")
        or row.get("event_state_inputs")
        or row.get("events")
        or []
    )
    if isinstance(events, str):
        events = _coerce_payload(events)
    if isinstance(events, Mapping):
        events = [events]
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return []
    return [event for event in events if isinstance(event, Mapping)]


def _event_refs(events: Sequence[Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for event in events:
        ref = event.get("event_family_contract_ref") or event.get("canonical_event_id") or event.get("event_id")
        if ref:
            refs.append(str(ref))
    return refs


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("background_context_state", "target_context_state", "accepted_event_contracts", "accepted_event_contexts", "event_state_inputs", "events"):
        output[key] = _coerce_payload(output.get(key))
    return output


def _payload(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = _coerce_payload(row.get(key))
    return dict(value) if isinstance(value, Mapping) else {}


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
                raise ValueError(f"forbidden M03 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

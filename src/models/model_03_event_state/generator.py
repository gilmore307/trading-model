"""EventStateModel deterministic pilot generator."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import (
    DEFAULT_EVENT_EFFECT_MODEL,
    EVENT_DISTRIBUTION_EFFECT_CHANNELS,
    EVENT_IMPACT_CHANNELS,
    FORBIDDEN_OUTPUT_FIELDS,
    HORIZONS,
    MODEL_ID,
    MODEL_STEP,
    MODEL_VERSION,
)

ET = ZoneInfo("America/New_York")
SCOPE_KEYS = ("market", "sector", "industry", "theme_factor", "peer_group", "symbol", "microstructure")
HORIZON_MINUTES = {"10min": 10, "1h": 60, "1D": 24 * 60, "1W": 7 * 24 * 60}


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
    events = _event_rows(row, _row_time(row))
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
            "scope_projection_scores": _scope_projection_vector(scores),
            "event_effect_models": _event_effect_model_refs(events),
            "frozen_event_contract_refs": _event_refs(events),
            "accepted_event_count": len(events),
            "event_parameter_mutation_allowed": False,
        },
        "event_state_diagnostics": {
            "accepted_event_count": len(events),
            "visible_event_ids": [event.get("event_id") for event in events],
            "canonical_event_count": sum(
                1
                for event in events
                if event.get("dedup_status") not in {"covered_by_canonical_event", "duplicate", "covered"}
            ),
            "only_point_in_time_accepted_events": True,
            "no_standalone_event_alpha": True,
            "event_effect_model_channel_enforced": True,
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
    weights = [_event_weight(event, horizon) for event in events]
    intensities = [_score(event, "event_intensity_score", "intensity_score", default=0.35) for event in events]
    uncertainties = [_score(event, "uncertainty_score", "revision_risk_score", default=0.25) for event in events]
    direction_biases = [_directional_signal(event) for event in events]
    relevance = [_score(event, "target_relevance_score", "applicability_confidence_score", default=0.50) for event in events]
    risk_scores = [
        _score(event, "path_risk_score", "gap_risk_score", "event_path_risk_score", default=intensity * (0.45 + 0.35 * uncertainty))
        for event, intensity, uncertainty in zip(events, intensities, uncertainties)
    ]
    intensity = _weighted_average(intensities, weights)
    uncertainty = _weighted_average(uncertainties, weights)
    response_direction = _clip_signed(_weighted_average(direction_biases, weights) * max(_weighted_average(relevance, weights), 0.25))
    response_strength = _clip01(intensity * max(abs(response_direction), 0.35))
    path_risk = _clip01(_weighted_average(risk_scores, weights))
    entry_block = _clip01(_average([path_risk, uncertainty, max(0.0, -response_direction * target_direction)]))
    exposure_cap = _clip01(_average([path_risk, uncertainty * 0.75]))
    disable = _clip01(max(0.0, path_risk - 0.70) + max(0.0, uncertainty - 0.80))
    applicability = _clip01(_weighted_average(relevance, weights))
    return {
        "event_response_direction_score": response_direction,
        "event_response_strength_score": response_strength,
        "event_uncertainty_score": uncertainty,
        "event_path_risk_score": path_risk,
        "event_entry_block_pressure_score": entry_block,
        "event_exposure_cap_pressure_score": exposure_cap,
        "event_strategy_disable_pressure_score": disable,
        "event_applicability_confidence_score": applicability,
        **_impact_channel_scores(events, weights),
        **_distribution_effect_scores(events, weights),
        **_scope_projection_scores(events, weights),
    }


def _score_payload(horizon_payloads: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for horizon, payload in horizon_payloads.items():
        for name, value in payload.items():
            output[f"3_{name}_{horizon}"] = round(value, 6)
    return output


def _impact_channel_scores(events: Sequence[Mapping[str, Any]], weights: Sequence[float]) -> dict[str, float]:
    return {
        "event_underlying_price_impact_score": _average_channel(
            events,
            weights,
            "underlying_price",
            "underlying_price_impact_score",
            "underlying_impact_score",
        ),
        "event_option_price_impact_score": _average_channel(
            events,
            weights,
            "option_price",
            "option_price_impact_score",
            "option_impact_score",
        ),
        "event_volatility_surface_impact_score": _average_channel(
            events,
            weights,
            "volatility_surface",
            "volatility_surface_impact_score",
            "vol_surface_impact_score",
        ),
        "event_option_liquidity_spread_impact_score": _average_channel(
            events,
            weights,
            "option_liquidity_spread",
            "option_liquidity_spread_impact_score",
            "liquidity_spread_impact_score",
        ),
        "event_expiry_gamma_flow_impact_score": _average_channel(
            events,
            weights,
            "expiry_gamma_flow",
            "expiry_gamma_flow_impact_score",
            "gamma_flow_impact_score",
        ),
    }


def _empty_impact_channel_scores() -> dict[str, float]:
    return {f"event_{channel}_impact_score": 0.0 for channel in EVENT_IMPACT_CHANNELS}


def _empty_distribution_effect_scores() -> dict[str, float]:
    return {f"event_{channel}_score": 0.0 for channel in EVENT_DISTRIBUTION_EFFECT_CHANNELS}


def _average_channel(events: Sequence[Mapping[str, Any]], weights: Sequence[float], channel: str, *keys: str) -> float:
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
    return _clip01(_weighted_average(values, weights[: len(values)]))


def _impact_channel_vector(scores: Mapping[str, float]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for horizon in HORIZONS:
        output[horizon] = {
            channel: float(scores.get(f"3_event_{channel}_impact_score_{horizon}", 0.0))
            for channel in EVENT_IMPACT_CHANNELS
        }
    return output


def _distribution_effect_scores(events: Sequence[Mapping[str, Any]], weights: Sequence[float]) -> dict[str, float]:
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
        channels = _event_effect_channel_policy(event)
        intensity = _score(event, "event_intensity_score", "intensity_score", default=0.35)
        uncertainty = _score(event, "uncertainty_score", "revision_risk_score", default=0.25)
        path_risk = _score(event, "path_risk_score", "gap_risk_score", "event_path_risk_score", default=intensity * (0.45 + 0.35 * uncertainty))
        relevance = _score(event, "target_relevance_score", "applicability_confidence_score", default=0.50)
        raw_direction = _signed(event, "event_response_direction_score", "direction_bias_score", "surprise_score", default=0.0)
        directional_signal = _directional_signal(event)
        if channels["mean_shift"]:
            mean_shifts.append(_signed_or_default(event, directional_signal * intensity * relevance, "mean_shift_score", "event_mean_shift_score"))
        if channels["mode_shift"]:
            mode_shifts.append(_signed_or_default(event, directional_signal * intensity * relevance, "mode_shift_score", "event_mode_shift_score"))
        if channels["directional_contribution"]:
            contributions.append(_signed_or_default(event, directional_signal * intensity * relevance, "directional_contribution_score", "event_directional_contribution_score"))
        if channels["variance_multiplier"]:
            variances.append(_score(event, "variance_multiplier_score", "event_variance_multiplier_score", default=_clip01(0.55 * uncertainty + 0.45 * path_risk)))
        if channels["left_tail_delta"]:
            left_tails.append(_score(event, "left_tail_delta_score", "event_left_tail_delta_score", default=_clip01(path_risk * (1.0 + 0.35 * max(0.0, -raw_direction)))))
        if channels["right_tail_delta"]:
            right_tails.append(_score(event, "right_tail_delta_score", "event_right_tail_delta_score", default=_clip01(path_risk * (1.0 + 0.35 * max(0.0, raw_direction)))))
        if channels["skew_delta"]:
            skews.append(_signed_or_default(event, raw_direction * intensity * relevance, "skew_delta_score", "event_skew_delta_score"))
        if channels["confidence_discount"]:
            confidence_discounts.append(_score(event, "confidence_discount_score", "event_confidence_discount_score", default=_clip01(uncertainty * relevance)))
        if channels["gate_pressure"]:
            gates.append(_score(event, "gate_pressure_score", "event_gate_pressure_score", default=_clip01(_average([path_risk, uncertainty, intensity * 0.5]))))
    return {
        "event_mean_shift_score": _clip_signed(_weighted_average(mean_shifts, weights[: len(mean_shifts)])),
        "event_mode_shift_score": _clip_signed(_weighted_average(mode_shifts, weights[: len(mode_shifts)])),
        "event_directional_contribution_score": _clip_signed(_weighted_average(contributions, weights[: len(contributions)])),
        "event_variance_multiplier_score": _clip01(_weighted_average(variances, weights[: len(variances)])),
        "event_left_tail_delta_score": _clip01(_weighted_average(left_tails, weights[: len(left_tails)])),
        "event_right_tail_delta_score": _clip01(_weighted_average(right_tails, weights[: len(right_tails)])),
        "event_skew_delta_score": _clip_signed(_weighted_average(skews, weights[: len(skews)])),
        "event_confidence_discount_score": _clip01(_weighted_average(confidence_discounts, weights[: len(confidence_discounts)])),
        "event_gate_pressure_score": _clip01(_weighted_average(gates, weights[: len(gates)])),
    }


def _distribution_effect_vector(scores: Mapping[str, float]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for horizon in HORIZONS:
        output[horizon] = {
            channel: float(scores.get(f"3_event_{channel}_score_{horizon}", 0.0))
            for channel in EVENT_DISTRIBUTION_EFFECT_CHANNELS
        }
    return output


def _scope_projection_scores(events: Sequence[Mapping[str, Any]], weights: Sequence[float]) -> dict[str, float]:
    output: dict[str, float] = {}
    for scope in SCOPE_KEYS:
        output[f"event_{scope}_impact_score"] = _clip_signed(
            _weighted_average(
                [
                    _safe_float((event.get("impact_scores") or {}).get(scope))
                    if isinstance(event.get("impact_scores"), Mapping)
                    else None
                    for event in events
                ],
                weights,
            )
        )
    output["event_scope_confidence_score"] = _clip01(
        _weighted_average([_score(event, "scope_confidence_score", "event_scope_confidence_score", default=0.0) for event in events], weights)
    )
    output["event_scope_escalation_risk_score"] = _clip01(
        _weighted_average(
            [_score(event, "scope_escalation_risk_score", "event_scope_escalation_risk_score", default=0.0) for event in events],
            weights,
        )
    )
    output["event_target_relevance_score"] = _clip01(
        _weighted_average([_score(event, "target_relevance_score", "event_target_relevance_score", default=0.0) for event in events], weights)
    )
    return output


def _scope_projection_vector(scores: Mapping[str, float]) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for horizon in HORIZONS:
        output[horizon] = {
            scope: float(scores.get(f"3_event_{scope}_impact_score_{horizon}", 0.0))
            for scope in SCOPE_KEYS
        }
        output[horizon]["scope_confidence"] = float(scores.get(f"3_event_scope_confidence_score_{horizon}", 0.0))
        output[horizon]["scope_escalation_risk"] = float(scores.get(f"3_event_scope_escalation_risk_score_{horizon}", 0.0))
        output[horizon]["target_relevance"] = float(scores.get(f"3_event_target_relevance_score_{horizon}", 0.0))
    return output


def _event_effect_model_refs(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for event in events:
        models.append(
            {
                "event_ref": event.get("event_family_contract_ref") or event.get("canonical_event_id") or event.get("event_id"),
                "event_family_key": event.get("event_family_key") or event.get("mechanism_family") or event.get("normalized_event_type"),
                "semantic_taxonomy_node_ref": event.get("semantic_taxonomy_node_ref") or event.get("taxonomy_node_ref"),
                "effect_model_node_ref": event.get("effect_model_node_ref") or event.get("event_family_key") or event.get("mechanism_family"),
                "event_effect_model": _event_effect_model(event),
            }
        )
    return models


def _directional_signal(event: Mapping[str, Any]) -> float:
    channels = _event_effect_channel_policy(event)
    if not (channels["mean_shift"] or channels["mode_shift"] or channels["directional_contribution"]):
        return 0.0
    return _signed(event, "event_response_direction_score", "direction_bias_score", "surprise_score", default=0.0)


def _event_effect_model(event: Mapping[str, Any]) -> dict[str, Any]:
    model = dict(DEFAULT_EVENT_EFFECT_MODEL)
    raw_model = event.get("event_effect_model") or event.get("event_family_effect_model") or {}
    if isinstance(raw_model, Mapping):
        for key in ("event_effect_model_type", "projection_mode", "directional_mean_shift_status"):
            if key in raw_model:
                model[key] = str(raw_model.get(key) or "").strip()
        for key in ("distribution_channels", "impact_channels"):
            channels = raw_model.get(key)
            if isinstance(channels, Sequence) and not isinstance(channels, (str, bytes, bytearray)):
                model[key] = tuple(str(channel).strip() for channel in channels if str(channel).strip())
    return model


def _event_effect_channel_policy(event: Mapping[str, Any]) -> dict[str, bool]:
    model = _event_effect_model(event)
    distribution_channels = model.get("distribution_channels")
    allowed = set(distribution_channels) if isinstance(distribution_channels, Sequence) else set()
    return {channel: channel in allowed for channel in EVENT_DISTRIBUTION_EFFECT_CHANNELS}


def _signed_or_default(row: Mapping[str, Any], default: float, *keys: str) -> float:
    for key in keys:
        value = _safe_float(row.get(key))
        if value is not None:
            return _clip_signed(value)
    return _clip_signed(default)


def _event_rows(row: Mapping[str, Any], decision_time: datetime) -> list[Mapping[str, Any]]:
    raw_events: list[Mapping[str, Any]] = []
    for key in (
        "accepted_event_contracts",
        "accepted_event_contexts",
        "event_state_inputs",
        "event_observations",
        "model_03_event_state_data_acquisition",
        "events",
    ):
        value = _coerce_payload(row.get(key))
        if isinstance(value, Mapping) and value:
            raw_events.append(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            raw_events.extend(event for event in value if isinstance(event, Mapping))
    visible: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for event in raw_events:
        event_available = _parse_time(
            event.get("available_time")
            or event.get("ingested_time")
            or event.get("event_time")
            or row.get("available_time")
        )
        if event_available > decision_time:
            continue
        normalized = _normalize_event(event, row, decision_time)
        event_key = str(normalized.get("canonical_event_id") or normalized.get("event_id") or repr(sorted(normalized.items())))
        if event_key in seen:
            continue
        seen.add(event_key)
        visible.append(normalized)
    return visible


def _event_refs(events: Sequence[Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for event in events:
        ref = event.get("event_family_contract_ref") or event.get("canonical_event_id") or event.get("event_id")
        if ref:
            refs.append(str(ref))
    return refs


def _normalize_event(event: Mapping[str, Any], row: Mapping[str, Any], decision_time: datetime) -> dict[str, Any]:
    output = dict(event)
    interpretation = _interpretation_payload(event)
    normalized_type = interpretation.get("normalized_event_type")
    if normalized_type:
        output.setdefault("event_category_type", normalized_type)
        output.setdefault("event_family_key", normalized_type)
    channels = interpretation.get("impact_channels")
    if isinstance(channels, Mapping):
        output.setdefault("impact_channels", channels)
    event_time = _parse_time(event.get("event_time") or event.get("event_actual_time") or event.get("available_time") or row.get("available_time"))
    output["event_time"] = _iso(event_time)
    output["age_minutes"] = round((decision_time - event_time).total_seconds() / 60.0, 4)
    dedup_status = str(event.get("dedup_status") or "new_information").lower()
    output["dedup_status"] = dedup_status
    output["dedup_weight"] = 0.25 if dedup_status in {"covered_by_canonical_event", "duplicate", "covered"} else 1.0
    native_scope = str(_scope_from_interpretation(interpretation) or event.get("event_native_scope_type") or event.get("scope_type") or _scope_from_event(output)).lower()
    output["event_native_scope_type"] = native_scope
    relevance = _score(event, "target_relevance_score", "event_target_relevance_score", default=_target_relevance(event, row, native_scope))
    output.setdefault("target_relevance_score", relevance)
    intensity = _score(interpretation, "intensity_score", default=_score(event, "event_intensity_score", "intensity_score", "surprise_abs_score", default=0.35))
    uncertainty = _score(interpretation, "uncertainty_score", default=_score(event, "uncertainty_score", "revision_risk_score", default=0.25))
    direction = _signed(interpretation, "direction_bias_score", default=_signed(event, "direction_bias_score", "event_response_direction_score", "surprise_score", default=0.0))
    output.setdefault("event_intensity_score", intensity)
    output.setdefault("uncertainty_score", uncertainty)
    output.setdefault("direction_bias_score", direction)
    output.setdefault("impact_scores", _impact_scores(output, native_scope, relevance, intensity, direction))
    output.setdefault("scope_confidence_score", _score(event, "scope_confidence_score", default=0.75 if native_scope != "unknown" else 0.35))
    output.setdefault(
        "scope_escalation_risk_score",
        _score(
            event,
            "scope_escalation_risk_score",
            default=max(
                abs(float(output["impact_scores"].get("market", 0.0))),
                abs(float(output["impact_scores"].get("sector", 0.0))),
                abs(float(output["impact_scores"].get("theme_factor", 0.0))),
            )
            * intensity
            * 0.5,
        ),
    )
    output.setdefault("liquidity_disruption_score", _score(event, "liquidity_disruption_score", default=intensity * (1.0 if native_scope == "microstructure" else 0.35)))
    output.setdefault("contagion_risk_score", _score(event, "contagion_risk_score", default=_score(output, "scope_escalation_risk_score", default=0.0) * intensity))
    return output


def _interpretation_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("event_interpretation", "event_interpretation_v1", "standardized_event_interpretation"):
        value = event.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _scope_from_interpretation(interpretation: Mapping[str, Any]) -> str:
    scope = interpretation.get("affected_scope")
    if isinstance(scope, str):
        return scope
    if isinstance(scope, Mapping):
        for key in ("primary_scope", "scope_type", "event_native_scope_type"):
            value = scope.get(key)
            if value:
                return str(value)
    return ""


def _scope_from_event(event: Mapping[str, Any]) -> str:
    category = str(event.get("event_category_type") or event.get("event_family_key") or event.get("event_family") or "").lower()
    if any(token in category for token in ("option", "expiry", "witch", "gamma", "volatility", "iv")):
        return "microstructure"
    if event.get("symbol") or any(token in category for token in ("sec", "earnings", "analyst", "litigation", "halt")):
        return "symbol"
    if event.get("sector_type") or "sector" in category:
        return "sector"
    if any(token in category for token in ("macro", "market", "rates", "inflation", "fed")):
        return "market"
    return "unknown"


def _target_relevance(event: Mapping[str, Any], row: Mapping[str, Any], native_scope: str) -> float:
    event_symbol = str(event.get("symbol") or "").upper()
    row_symbol = str(row.get("symbol_for_join_only") or row.get("symbol") or "").upper()
    if event_symbol and row_symbol and event_symbol == row_symbol:
        return 1.0
    event_sector = str(event.get("sector_type") or "").lower()
    row_sector = str(row.get("sector_type") or "").lower()
    if event_sector and row_sector and event_sector == row_sector:
        return 0.65
    if native_scope in {"market", "theme_factor", "microstructure"}:
        return 0.45
    return 0.35


def _impact_scores(
    event: Mapping[str, Any],
    native_scope: str,
    relevance: float,
    intensity: float,
    direction_bias: float,
) -> dict[str, float]:
    raw = event.get("impact_scores")
    impact_scores = {scope: 0.0 for scope in SCOPE_KEYS}
    if isinstance(raw, Mapping):
        impact_scores.update({scope: _clip_signed(_safe_float(raw.get(scope))) for scope in SCOPE_KEYS if scope in raw})
    else:
        signed_impact = _clip_signed(direction_bias * max(relevance, 0.2))
        if native_scope in impact_scores:
            impact_scores[native_scope] = signed_impact
        if native_scope == "symbol":
            impact_scores["peer_group"] = _clip_signed(signed_impact * 0.35)
        elif native_scope == "sector":
            impact_scores["industry"] = _clip_signed(signed_impact * 0.55)
            impact_scores["market"] = _clip_signed(signed_impact * 0.25)
        elif native_scope == "market":
            impact_scores["sector"] = _clip_signed(signed_impact * 0.45)
            impact_scores["theme_factor"] = _clip_signed(signed_impact * 0.35)
        elif native_scope == "microstructure":
            impact_scores["symbol"] = _clip_signed(signed_impact * 0.55)
        elif direction_bias == 0 and native_scope in impact_scores:
            impact_scores[native_scope] = _clip_signed(intensity * relevance)
    return {scope: round(value, 6) for scope, value in impact_scores.items()}


def _event_weight(event: Mapping[str, Any], horizon: str) -> float:
    horizon_minutes = HORIZON_MINUTES[horizon]
    age_minutes = abs(float(event.get("age_minutes") or 0.0))
    time_weight = _clip01(math.exp(-age_minutes / max(float(horizon_minutes), 1.0)))
    return time_weight * _clip01(_safe_float(event.get("dedup_weight")) or 1.0)


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in (
        "background_context_state",
        "target_context_state",
        "accepted_event_contracts",
        "accepted_event_contexts",
        "event_state_inputs",
        "event_observations",
        "model_03_event_state_data_acquisition",
        "events",
    ):
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
    if value is None:
        return {}
    return value


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


def _weighted_average(values: Iterable[float | None], weights: Sequence[float], *, default: float = 0.0) -> float:
    clean: list[tuple[float, float]] = []
    for index, value in enumerate(values):
        if value is None:
            continue
        weight = float(weights[index]) if index < len(weights) else 1.0
        if weight > 0:
            clean.append((float(value), weight))
    total = sum(weight for _value, weight in clean)
    if total <= 0:
        return default
    return sum(value * weight for value, weight in clean) / total


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

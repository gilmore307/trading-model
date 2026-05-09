"""Deterministic EventOverlayModel V1 scaffold.

The generator converts point-in-time visible event overview/detail rows into an
``event_context_vector``. It filters by ``event.available_time <= decision
available_time``, discounts covered duplicates, separates native scope from
impact scope, and avoids alpha/action/execution fields.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZON_MINUTES, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION

ET = ZoneInfo("America/New_York")
SCOPE_KEYS = ("market", "sector", "industry", "theme_factor", "peer_group", "symbol", "microstructure")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 4 decision row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or row.get("scope_key") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_dt = _row_time(row)
    available_time = _iso(available_dt)
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or row.get("scope_key") or "scope").strip()
    events = [_encode_event(event, available_dt, row) for event in _visible_events(row, available_dt)]
    payload: dict[str, Any] = {}
    audit: dict[str, Any] = {}
    for horizon in HORIZONS:
        scores = _horizon_scores(events, horizon)
        suffix = _suffix(horizon)
        payload.update({f"4_event_{key}_score_{suffix}": scores[key] for key in (
            "presence", "timing_proximity", "intensity", "uncertainty", "gap_risk",
            "reversal_risk", "liquidity_disruption", "contagion_risk", "context_quality",
        )})
        payload[f"4_event_direction_bias_score_{suffix}"] = scores["direction_bias"]
        payload[f"4_event_context_alignment_score_{suffix}"] = scores["context_alignment"]
        for scope in SCOPE_KEYS:
            payload[f"4_event_{scope}_impact_score_{suffix}"] = scores[f"{scope}_impact"]
        payload[f"4_event_scope_confidence_score_{suffix}"] = scores["scope_confidence"]
        payload[f"4_event_scope_escalation_risk_score_{suffix}"] = scores["scope_escalation_risk"]
        payload[f"4_event_target_relevance_score_{suffix}"] = scores["target_relevance"]
        audit[f"4_event_dominant_impact_scope_{suffix}"] = scores["dominant_impact_scope"]

    ref = _stable_id("ecv", target_candidate_id, available_time, model_version)
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "market_context_state_ref": row.get("market_context_state_ref"),
        "sector_context_state_ref": row.get("sector_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref"),
        "event_context_vector_ref": ref,
        **payload,
        "event_context_vector": payload,
        "event_overlay_diagnostics": {
            "visible_event_count": len(events),
            "canonical_event_count": sum(1 for event in events if event.get("dedup_status") not in {"covered_by_canonical_event", "duplicate", "covered"}),
            "visible_event_ids": [event.get("event_id") for event in events],
            "dominant_impact_scope_by_horizon": audit,
            "encoded_events": events,
        },
    }
    _validate_no_forbidden_output(output)
    return output


def _visible_events(row: Mapping[str, Any], decision_available_time: datetime) -> list[Mapping[str, Any]]:
    event_rows = row.get("source_04_event_overlay") or row.get("event_rows") or row.get("events") or []
    if isinstance(event_rows, Mapping):
        event_rows = [event_rows]
    visible: list[Mapping[str, Any]] = []
    for event in event_rows if isinstance(event_rows, Sequence) and not isinstance(event_rows, (str, bytes, bytearray)) else []:
        if not isinstance(event, Mapping):
            continue
        event_available = _parse_time(event.get("available_time") or event.get("ingested_time") or event.get("event_time"))
        if event_available <= decision_available_time:
            visible.append(event)
    return visible


def _encode_event(event: Mapping[str, Any], decision_time: datetime, row: Mapping[str, Any]) -> dict[str, Any]:
    event_time = _parse_time(event.get("event_time") or event.get("event_actual_time") or event.get("available_time"))
    age_minutes = (decision_time - event_time).total_seconds() / 60.0
    abs_age_minutes = abs(age_minutes)
    dedup_status = str(event.get("dedup_status") or "new_information").lower()
    dedup_weight = 0.25 if dedup_status in {"covered_by_canonical_event", "duplicate", "covered"} else 1.0
    source_priority = _safe_float(event.get("source_priority"))
    source_quality = _clip01(_safe_float(event.get("source_quality_score")) if _safe_float(event.get("source_quality_score")) is not None else (1.0 / max(source_priority or 1.0, 1.0)))
    intensity = _event_intensity(event) * dedup_weight
    direction_bias = _clip_signed(_first_float(event, "direction_bias_score", "event_direction_bias_score", "surprise_score", "abnormal_return_score") or 0.0)
    uncertainty = _clip01(_first_float(event, "uncertainty_score", "revision_risk_score") if _first_float(event, "uncertainty_score", "revision_risk_score") is not None else (0.55 if dedup_status in {"conflicting", "revised"} else 0.25))
    inferred_native_scope = _scope_from_category(event)
    native_scope = str(
        event.get("event_native_scope_type")
        or (
            inferred_native_scope
            if inferred_native_scope in {"equity_abnormal_activity", "option_abnormal_activity", "price_action"}
            else None
        )
        or event.get("scope_type")
        or inferred_native_scope
    ).lower()
    relevance = _target_relevance(event, row, native_scope)
    impact = {scope: _impact_score(event, native_scope, scope, relevance, intensity) for scope in SCOPE_KEYS}
    scope_confidence = _clip01(_first_float(event, "scope_confidence_score") if _first_float(event, "scope_confidence_score") is not None else (0.75 if native_scope != "unknown" else 0.35))
    escalation = _clip01(_first_float(event, "scope_escalation_risk_score") if _first_float(event, "scope_escalation_risk_score") is not None else max(impact["market"], impact["sector"], impact["theme_factor"]) * 0.5)
    gap_risk = _clip01(_first_float(event, "gap_risk_score") if _first_float(event, "gap_risk_score") is not None else intensity * (0.8 if abs_age_minutes <= 60 else 0.35))
    reversal_risk = _clip01(_first_float(event, "reversal_risk_score") if _first_float(event, "reversal_risk_score") is not None else uncertainty * max(intensity, 0.25))
    liquidity_risk = _clip01(
        _first_float(event, "liquidity_disruption_score")
        if _first_float(event, "liquidity_disruption_score") is not None
        else intensity
        * (1.0 if native_scope in {"microstructure", "option_abnormal_activity", "equity_abnormal_activity", "price_action"} else 0.35)
    )
    contagion = _clip01(_first_float(event, "contagion_risk_score") if _first_float(event, "contagion_risk_score") is not None else max(impact["market"], impact["sector"], escalation) * intensity)
    quality = _clip01(_first_float(event, "event_context_quality_score", "quality_score") if _first_float(event, "event_context_quality_score", "quality_score") is not None else source_quality * (1.0 - uncertainty * 0.35))
    target_direction = _first_float(_payload(row, "target_context_state"), "3_target_direction_score_390min", "3_target_direction_score_60min") or 0.0
    alignment = _clip_signed(direction_bias * (1 if target_direction >= 0 else -1) * relevance)
    return {
        "event_id": event.get("event_id"),
        "canonical_event_id": event.get("canonical_event_id"),
        "dedup_status": dedup_status,
        "dedup_weight": round(dedup_weight, 4),
        "event_time": _iso(event_time),
        "age_minutes": round(age_minutes, 4),
        "event_native_scope_type": native_scope,
        "event_lifecycle_state": _lifecycle_state(age_minutes),
        "event_base_intensity": round(intensity, 6),
        "event_base_direction_bias": direction_bias,
        "event_base_uncertainty": uncertainty,
        "event_base_quality": quality,
        "event_target_relevance_score": relevance,
        "event_context_alignment_score": alignment,
        "event_gap_risk_score": gap_risk,
        "event_reversal_risk_score": reversal_risk,
        "event_liquidity_disruption_score": liquidity_risk,
        "event_contagion_risk_score": contagion,
        "event_scope_confidence_score": scope_confidence,
        "event_scope_escalation_risk_score": escalation,
        "impact_scores": impact,
    }


def _horizon_scores(events: Sequence[Mapping[str, Any]], horizon: str) -> dict[str, Any]:
    minutes = HORIZON_MINUTES[horizon]
    if not events:
        return _no_event_scores()
    weights = [_time_weight(event, minutes) * float(event.get("dedup_weight") or 1.0) for event in events]
    presence = _clip01(sum(1.0 for weight in weights if weight > 0) / 3.0)
    proximity = _clip01(max(weights) if weights else 0.0)
    intensity = _weighted_average([_safe_float(event.get("event_base_intensity")) for event in events], weights, default=0.0)
    relevance = _weighted_average([_safe_float(event.get("event_target_relevance_score")) for event in events], weights, default=0.0)
    scores: dict[str, Any] = {
        "presence": presence,
        "timing_proximity": proximity,
        "intensity": intensity,
        "direction_bias": _clip_signed(_weighted_average([_safe_float(event.get("event_base_direction_bias")) for event in events], weights, default=0.0)),
        "context_alignment": _clip_signed(_weighted_average([_safe_float(event.get("event_context_alignment_score")) for event in events], weights, default=0.0)),
        "uncertainty": _weighted_average([_safe_float(event.get("event_base_uncertainty")) for event in events], weights, default=0.0),
        "gap_risk": _weighted_average([_safe_float(event.get("event_gap_risk_score")) for event in events], weights, default=0.0),
        "reversal_risk": _weighted_average([_safe_float(event.get("event_reversal_risk_score")) for event in events], weights, default=0.0),
        "liquidity_disruption": _weighted_average([_safe_float(event.get("event_liquidity_disruption_score")) for event in events], weights, default=0.0),
        "contagion_risk": _weighted_average([_safe_float(event.get("event_contagion_risk_score")) for event in events], weights, default=0.0),
        "context_quality": _weighted_average([_safe_float(event.get("event_base_quality")) for event in events], weights, default=0.75),
        "scope_confidence": _weighted_average([_safe_float(event.get("event_scope_confidence_score")) for event in events], weights, default=0.0),
        "scope_escalation_risk": _weighted_average([_safe_float(event.get("event_scope_escalation_risk_score")) for event in events], weights, default=0.0),
        "target_relevance": relevance,
    }
    impact_values: dict[str, float] = {}
    for scope in SCOPE_KEYS:
        values = [_safe_float((event.get("impact_scores") or {}).get(scope)) for event in events]
        impact_values[f"{scope}_impact"] = _weighted_average(values, weights, default=0.0)
    scores.update(impact_values)
    dominant = max(SCOPE_KEYS, key=lambda scope: scores[f"{scope}_impact"])
    scores["dominant_impact_scope"] = dominant if scores[f"{dominant}_impact"] > 0 else "none"
    return {key: (round(value, 6) if isinstance(value, float) else value) for key, value in scores.items()}


def _no_event_scores() -> dict[str, Any]:
    scores: dict[str, Any] = {
        "presence": 0.0,
        "timing_proximity": 0.0,
        "intensity": 0.0,
        "direction_bias": 0.0,
        "context_alignment": 0.0,
        "uncertainty": 0.0,
        "gap_risk": 0.0,
        "reversal_risk": 0.0,
        "liquidity_disruption": 0.0,
        "contagion_risk": 0.0,
        "context_quality": 0.8,
        "scope_confidence": 0.0,
        "scope_escalation_risk": 0.0,
        "target_relevance": 0.0,
        "dominant_impact_scope": "none",
    }
    for scope in SCOPE_KEYS:
        scores[f"{scope}_impact"] = 0.0
    return scores


def _time_weight(event: Mapping[str, Any], horizon_minutes: int) -> float:
    age = abs(float(event.get("age_minutes") or 0.0))
    return _clip01(math.exp(-age / max(horizon_minutes, 1)))


def _event_intensity(event: Mapping[str, Any]) -> float:
    explicit = _first_float(event, "event_intensity_score", "intensity_score", "surprise_abs_score", "abnormal_activity_score")
    if explicit is not None:
        return _clip01(explicit)
    category = str(event.get("event_category_type") or event.get("information_role_type") or "").lower()
    if any(term in category for term in ("earnings", "sec", "macro", "guidance", "m&a", "merger")):
        return 0.8
    if any(
        term in category
        for term in ("abnormal", "breaking", "halt", "price_action", "breakout", "breakdown", "sweep", "trap")
    ):
        return 0.7
    if category:
        return 0.45
    return 0.25


def _target_relevance(event: Mapping[str, Any], row: Mapping[str, Any], native_scope: str) -> float:
    explicit = _first_float(event, "target_relevance_score", "event_target_relevance_score")
    if explicit is not None:
        return _clip01(explicit)
    event_symbol = str(event.get("symbol") or "").lower()
    join_symbol = str(row.get("symbol_for_join_only") or row.get("symbol") or "").lower()
    if event_symbol and join_symbol and event_symbol == join_symbol:
        return 1.0
    event_sector = str(event.get("sector_type") or "").lower()
    row_sector = str(row.get("sector_type") or "").lower()
    if event_sector and row_sector and event_sector == row_sector:
        return 0.7
    if native_scope in {"macro", "geopolitical", "market_structure", "market"}:
        return 0.55
    if native_scope in {"sector", "industry", "theme"}:
        return 0.45
    return 0.25


def _impact_score(event: Mapping[str, Any], native_scope: str, scope: str, relevance: float, intensity: float) -> float:
    explicit = _first_float(event, f"{scope}_impact_score", f"event_{scope}_impact_score")
    if explicit is not None:
        return _clip01(explicit)
    scope_alias = {"theme_factor": "theme", "microstructure": "microstructure"}[scope] if scope in {"theme_factor", "microstructure"} else scope
    base = 1.0 if native_scope == scope_alias else 0.0
    if native_scope in {"macro", "geopolitical", "market_structure"} and scope == "market":
        base = 0.9
    if native_scope == "symbol" and scope in {"symbol", "peer_group", "sector"}:
        base = {"symbol": 1.0, "peer_group": 0.45, "sector": 0.25}[scope]
    if native_scope in {"equity_abnormal_activity", "option_abnormal_activity", "price_action"} and scope in {"symbol", "microstructure"}:
        base = {"symbol": 0.8, "microstructure": 0.9}[scope]
    return _clip01(base * max(relevance, 0.25) * max(intensity, 0.25))


def _scope_from_category(event: Mapping[str, Any]) -> str:
    category = str(event.get("event_category_type") or "").lower()
    if "macro" in category:
        return "macro"
    if "abnormal" in category:
        return "equity_abnormal_activity"
    if "option" in category:
        return "option_abnormal_activity"
    if any(term in category for term in ("price_action", "breakout", "breakdown", "sweep", "trap")):
        return "price_action"
    if "sec" in category or "filing" in category or event.get("symbol"):
        return "symbol"
    return "unknown"


def _lifecycle_state(age_minutes: float) -> str:
    if age_minutes < -60:
        return "scheduled_future"
    if age_minutes < 0:
        return "pre_event_window"
    if age_minutes <= 30:
        return "live_release_window"
    if age_minutes <= 390:
        return "post_event_initial_reaction"
    return "post_event_decay"


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("market_context_state", "sector_context_state", "target_context_state"):
        output[key] = _coerce_payload(output.get(key))
    events = output.get("source_04_event_overlay") or output.get("event_rows") or output.get("events") or []
    if isinstance(events, str):
        events = _coerce_payload(events)
    output["event_rows"] = events if isinstance(events, list) else [events] if isinstance(events, Mapping) else []
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


def _weighted_average(values: Iterable[float | None], weights: Iterable[float], *, default: float) -> float:
    pairs = [(value, weight) for value, weight in zip(values, weights) if value is not None and weight > 0]
    if not pairs:
        return default
    total_weight = sum(weight for _, weight in pairs)
    if total_weight <= 0:
        return default
    return sum(float(value) * weight for value, weight in pairs) / total_weight


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
                raise ValueError(f"forbidden Layer 4 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

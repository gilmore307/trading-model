"""EventStateModel deterministic pilot generator."""
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
            "frozen_event_contract_refs": _event_refs(events),
            "accepted_event_count": len(events),
            "event_parameter_mutation_allowed": False,
        },
        "event_state_diagnostics": {
            "accepted_event_count": len(events),
            "only_point_in_time_accepted_events": True,
            "no_standalone_event_alpha": True,
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
        }
    intensities = [_score(event, "event_intensity_score", "intensity_score", default=0.35) for event in events]
    uncertainties = [_score(event, "uncertainty_score", "revision_risk_score", default=0.25) for event in events]
    direction_biases = [_signed(event, "event_response_direction_score", "direction_bias_score", "surprise_score", default=0.0) for event in events]
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
    }


def _score_payload(horizon_payloads: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for horizon, payload in horizon_payloads.items():
        for name, value in payload.items():
            output[f"3_{name}_{horizon}"] = round(value, 6)
    return output


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

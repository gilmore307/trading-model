"""ResidualEventGovernanceModel generator.

M06 consumes the current M04 unified-decision thesis, optional M05 option
expression context, and point-in-time event observations. It emits current
``6_*`` residual-event governance scores plus an ``event_risk_intervention``
policy payload.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_STEP, MODEL_VERSION

ET = ZoneInfo("America/New_York")
SCOPE_KEYS = ("market", "sector", "industry", "theme_factor", "peer_group", "symbol", "microstructure")
HORIZON_MINUTES = {"10min": 10, "1h": 60, "1D": 24 * 60, "1W": 7 * 24 * 60}


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [dict(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one M06 residual event governance input row is required")
    rows.sort(key=lambda row: (str(row.get("available_time") or ""), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    decision_time = _parse_time(row.get("available_time"))
    available_time = _iso(decision_time)
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    encoded_events = [_encode_event(event, decision_time, row) for event in _visible_events(row, decision_time)]
    scores, dominant_by_horizon = _event_scores(encoded_events)
    policy = _intervention_policy(scores)
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    intervention_ref = _stable_id("eri", target_candidate_id, available_time, model_version)
    governed_context = _governed_decision_context(row)
    visible_event_ids = [event.get("event_id") for event in encoded_events]
    canonical_event_count = sum(
        1
        for event in encoded_events
        if event.get("dedup_status") not in {"covered_by_canonical_event", "duplicate", "covered"}
    )
    diagnostics = {
        "visible_event_count": len(encoded_events),
        "canonical_event_count": canonical_event_count,
        "visible_event_ids": visible_event_ids,
        "encoded_events": encoded_events,
    }

    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_step": MODEL_STEP,
        "model_version": model_version,
        "background_context_state_ref": row.get("background_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref"),
        "event_state_vector_ref": row.get("event_state_vector_ref"),
        "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
        "option_expression_plan_ref": row.get("option_expression_plan_ref"),
        "event_risk_intervention_ref": intervention_ref,
        **scores,
        **policy,
        "event_risk_intervention": {
            "governed_thesis_refs": {
                "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
                "option_expression_plan_ref": row.get("option_expression_plan_ref"),
            },
            "intervention_policy": policy,
            "residual_event_scores": scores,
            "dominant_impact_scope_by_horizon": dominant_by_horizon,
            "future_event_family_packet_eligibility": _future_packet_eligibility(policy, diagnostics),
            "governed_decision_context": governed_context,
        },
        "residual_event_governance_diagnostics": {
            **diagnostics,
            "dominant_impact_scope_by_horizon": dominant_by_horizon,
            "governed_decision_context": governed_context,
            "scoring_source": "model_06_native_residual_event_governance",
            "no_broker_or_account_mutation": True,
        },
    }
    if not output["option_expression_plan_ref"]:
        output.pop("option_expression_plan_ref")
        output["event_risk_intervention"]["governed_thesis_refs"].pop("option_expression_plan_ref")
    _validate_no_forbidden_output(output)
    return output


def _event_scores(events: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, str]]:
    scores: dict[str, Any] = {}
    dominant_by_horizon: dict[str, str] = {}
    for horizon in HORIZONS:
        payload = _horizon_scores(events, horizon)
        for key, value in payload.items():
            if key == "dominant_impact_scope":
                dominant_by_horizon[f"6_event_dominant_impact_scope_{horizon}"] = str(value)
            else:
                scores[f"6_event_{key}_score_{horizon}"] = value
    return scores, dominant_by_horizon


def _horizon_scores(events: Sequence[Mapping[str, Any]], horizon: str) -> dict[str, Any]:
    if not events:
        return _no_event_scores()
    minutes = HORIZON_MINUTES[horizon]
    weights = [_time_weight(event, minutes) * float(event.get("dedup_weight") or 1.0) for event in events]
    payload: dict[str, Any] = {
        "presence": _clip01(sum(1.0 for weight in weights if weight > 0) / 3.0),
        "timing_proximity": _clip01(max(weights) if weights else 0.0),
        "intensity": _weighted_average([_float(event.get("event_base_intensity")) for event in events], weights),
        "direction_bias": _clip_signed(_weighted_average([_float(event.get("event_base_direction_bias")) for event in events], weights)),
        "context_alignment": _clip_signed(_weighted_average([_float(event.get("event_context_alignment_score")) for event in events], weights)),
        "uncertainty": _weighted_average([_float(event.get("event_base_uncertainty")) for event in events], weights),
        "gap_risk": _weighted_average([_float(event.get("event_gap_risk_score")) for event in events], weights),
        "reversal_risk": _weighted_average([_float(event.get("event_reversal_risk_score")) for event in events], weights),
        "liquidity_disruption": _weighted_average([_float(event.get("event_liquidity_disruption_score")) for event in events], weights),
        "contagion_risk": _weighted_average([_float(event.get("event_contagion_risk_score")) for event in events], weights),
        "context_quality": _weighted_average([_float(event.get("event_base_quality")) for event in events], weights, default=0.75),
        "scope_confidence": _weighted_average([_float(event.get("event_scope_confidence_score")) for event in events], weights),
        "scope_escalation_risk": _weighted_average([_float(event.get("event_scope_escalation_risk_score")) for event in events], weights),
        "target_relevance": _weighted_average([_float(event.get("event_target_relevance_score")) for event in events], weights),
        "underlying_impact": _weighted_average([_float(event.get("underlying_impact_score")) for event in events], weights),
        "option_impact": _weighted_average([_float(event.get("option_impact_score")) for event in events], weights),
    }
    for scope in SCOPE_KEYS:
        payload[f"{scope}_impact"] = _weighted_average(
            [_float((event.get("impact_scores") or {}).get(scope)) for event in events],
            weights,
        )
    dominant = max(SCOPE_KEYS, key=lambda scope: abs(float(payload[f"{scope}_impact"])))
    payload["dominant_impact_scope"] = dominant if abs(float(payload[f"{dominant}_impact"])) > 0 else "none"
    return {key: (round(value, 6) if isinstance(value, float) else value) for key, value in payload.items()}


def _no_event_scores() -> dict[str, Any]:
    payload: dict[str, Any] = {
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
        "underlying_impact": 0.0,
        "option_impact": 0.0,
        "dominant_impact_scope": "none",
    }
    for scope in SCOPE_KEYS:
        payload[f"{scope}_impact"] = 0.0
    return payload


def _visible_events(row: Mapping[str, Any], decision_time: datetime) -> list[Mapping[str, Any]]:
    event_rows = (
        row.get("residual_event_observations")
        or row.get("event_observations")
        or row.get("model_06_residual_event_governance_data_acquisition")
        or row.get("events")
        or []
    )
    if isinstance(event_rows, Mapping):
        event_rows = [event_rows]
    if not isinstance(event_rows, Sequence) or isinstance(event_rows, (str, bytes, bytearray)):
        return []
    visible: list[Mapping[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, Mapping):
            continue
        event_available = _parse_time(event.get("available_time") or event.get("ingested_time") or event.get("event_time"))
        if event_available <= decision_time:
            visible.append(event)
    return visible


def _encode_event(event: Mapping[str, Any], decision_time: datetime, row: Mapping[str, Any]) -> dict[str, Any]:
    event_time = _parse_time(event.get("event_time") or event.get("event_actual_time") or event.get("available_time"))
    age_minutes = (decision_time - event_time).total_seconds() / 60.0
    dedup_status = str(event.get("dedup_status") or "new_information").lower()
    dedup_weight = 0.25 if dedup_status in {"covered_by_canonical_event", "duplicate", "covered"} else 1.0
    intensity = _score(event, "event_intensity_score", "intensity_score", "surprise_abs_score", default=0.35) * dedup_weight
    direction_bias = _signed(event, "direction_bias_score", "event_direction_bias_score", "surprise_score", default=0.0)
    uncertainty = _score(event, "uncertainty_score", "revision_risk_score", default=0.25)
    native_scope = str(event.get("event_native_scope_type") or event.get("scope_type") or _scope_from_event(event)).lower()
    relevance = _score(event, "target_relevance_score", "event_target_relevance_score", default=_target_relevance(event, row, native_scope))
    impact_scores = _impact_scores(event, native_scope, relevance, intensity, direction_bias)
    underlying_impact = _signed(event, "underlying_impact_score", "underlying_price_impact_score", default=impact_scores["symbol"] or direction_bias * relevance)
    option_impact = _score(event, "option_impact_score", "option_price_impact_score", default=_option_impact(event, native_scope, intensity, uncertainty))
    gap_risk = _score(event, "gap_risk_score", default=intensity * (0.8 if abs(age_minutes) <= 60 else 0.35))
    reversal_risk = _score(event, "reversal_risk_score", default=uncertainty * max(intensity, 0.25))
    liquidity_risk = _score(event, "liquidity_disruption_score", default=intensity * (1.0 if native_scope in {"microstructure", "option_abnormal_activity", "price_action"} else 0.35))
    broad_impact = max(abs(impact_scores["market"]), abs(impact_scores["sector"]), abs(impact_scores["theme_factor"]))
    escalation = _score(event, "scope_escalation_risk_score", default=broad_impact * 0.5)
    contagion = _score(event, "contagion_risk_score", default=max(broad_impact, escalation) * intensity)
    quality = _score(event, "event_context_quality_score", "quality_score", default=0.75 * (1.0 - uncertainty * 0.35) + 0.25)
    target_direction = _float(_payload(row, "target_context_state").get("2_target_direction_score_1W"))
    return {
        "event_id": event.get("event_id"),
        "canonical_event_id": event.get("canonical_event_id"),
        "dedup_status": dedup_status,
        "dedup_weight": round(dedup_weight, 4),
        "event_time": _iso(event_time),
        "age_minutes": round(age_minutes, 4),
        "event_native_scope_type": native_scope,
        "event_base_intensity": round(intensity, 6),
        "event_base_direction_bias": direction_bias,
        "event_base_uncertainty": uncertainty,
        "event_base_quality": quality,
        "event_target_relevance_score": relevance,
        "event_context_alignment_score": _clip_signed(direction_bias * (1 if target_direction >= 0 else -1) * relevance),
        "event_gap_risk_score": gap_risk,
        "event_reversal_risk_score": reversal_risk,
        "event_liquidity_disruption_score": liquidity_risk,
        "event_contagion_risk_score": contagion,
        "event_scope_confidence_score": _score(event, "scope_confidence_score", default=0.75 if native_scope != "unknown" else 0.35),
        "event_scope_escalation_risk_score": escalation,
        "impact_scores": impact_scores,
        "underlying_impact_score": underlying_impact,
        "option_impact_score": option_impact,
        "option_impact_mechanisms": _option_impact_mechanisms(event, option_impact),
    }


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        raise ValueError("M06 input requires point-in-time timestamp fields")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _time_weight(event: Mapping[str, Any], horizon_minutes: int) -> float:
    age_minutes = abs(_float(event.get("age_minutes")))
    return _clip01(math.exp(-age_minutes / max(float(horizon_minutes), 1.0)))


def _weighted_average(values: Sequence[float], weights: Sequence[float], *, default: float = 0.0) -> float:
    total_weight = sum(max(float(weight), 0.0) for weight in weights)
    if total_weight <= 0:
        return default
    return sum(float(value) * max(float(weight), 0.0) for value, weight in zip(values, weights)) / total_weight


def _clip01(value: Any) -> float:
    return max(0.0, min(1.0, _float(value)))


def _clip_signed(value: Any) -> float:
    return max(-1.0, min(1.0, _float(value)))


def _score(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row and row.get(key) is not None:
            return _clip01(row.get(key))
    return _clip01(default)


def _signed(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row and row.get(key) is not None:
            return _clip_signed(row.get(key))
    return _clip_signed(default)


def _payload(row: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = row.get(key)
    return value if isinstance(value, Mapping) else {}


def _scope_from_event(event: Mapping[str, Any]) -> str:
    category = str(event.get("event_category_type") or event.get("event_family") or "").lower()
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
        impact_scores.update({scope: _clip_signed(raw.get(scope)) for scope in SCOPE_KEYS if scope in raw})
    else:
        signed_impact = _clip_signed(direction_bias * max(relevance, 0.2))
        if native_scope in impact_scores:
            impact_scores[native_scope] = signed_impact
        elif native_scope == "option_abnormal_activity":
            impact_scores["microstructure"] = signed_impact
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
    for scope in SCOPE_KEYS:
        explicit_key = f"{scope}_impact_score"
        if explicit_key in event and event.get(explicit_key) is not None:
            impact_scores[scope] = _clip_signed(event.get(explicit_key))
        elif impact_scores[scope] == 0.0 and native_scope == scope and direction_bias == 0:
            impact_scores[scope] = _clip_signed(intensity * relevance)
    return {scope: round(value, 6) for scope, value in impact_scores.items()}


def _option_impact(event: Mapping[str, Any], native_scope: str, intensity: float, uncertainty: float) -> float:
    channels = event.get("impact_channels")
    if isinstance(channels, Mapping):
        channel_score = max(
            _float(channels.get("option_price")),
            _float(channels.get("volatility_surface")),
            _float(channels.get("expiry_gamma_flow")),
            _float(channels.get("option_liquidity_spread")),
        )
        if channel_score > 0:
            return _clip01(channel_score)
    category = str(event.get("event_category_type") or event.get("event_family") or "").lower()
    if any(token in category for token in ("option", "expiry", "witch", "gamma", "volatility", "iv")):
        return _clip01(max(intensity, 0.65))
    if native_scope in {"microstructure", "option_abnormal_activity"}:
        return _clip01(max(intensity * 0.85, 0.50))
    return _clip01(intensity * (0.45 + 0.35 * uncertainty))


def _option_impact_mechanisms(event: Mapping[str, Any], option_impact: float) -> list[str]:
    explicit = event.get("option_impact_mechanisms")
    if isinstance(explicit, Sequence) and not isinstance(explicit, (str, bytes, bytearray)):
        return sorted({str(item) for item in explicit if str(item)})
    category = str(event.get("event_category_type") or event.get("event_family") or "").lower()
    mechanisms: set[str] = set()
    if "witch" in category or "expiry" in category:
        mechanisms.add("expiry_gamma_flow")
    if "volatility" in category or "iv" in category:
        mechanisms.add("volatility_surface")
    if "option" in category:
        mechanisms.add("option_price")
    if option_impact >= 0.65:
        mechanisms.update({"option_price", "volatility_surface"})
    return sorted(mechanisms)


def _intervention_policy(scores: Mapping[str, Any]) -> dict[str, Any]:
    risk_by_horizon: dict[str, float] = {}
    reasons: list[str] = []
    for horizon in HORIZONS:
        suffix = horizon
        risk_by_horizon[horizon] = max(
            _float(scores.get(f"6_event_gap_risk_score_{suffix}")),
            _float(scores.get(f"6_event_reversal_risk_score_{suffix}")),
            _float(scores.get(f"6_event_liquidity_disruption_score_{suffix}")),
            _float(scores.get(f"6_event_contagion_risk_score_{suffix}")),
            _float(scores.get(f"6_event_scope_escalation_risk_score_{suffix}")),
        )
    risk_horizon = max(risk_by_horizon, key=lambda horizon: risk_by_horizon[horizon])
    severity = round(risk_by_horizon[risk_horizon], 6)
    presence = max(_float(scores.get(f"6_event_presence_score_{horizon}")) for horizon in HORIZONS)
    intensity = max(_float(scores.get(f"6_event_intensity_score_{horizon}")) for horizon in HORIZONS)
    option_impact = max(_float(scores.get(f"6_event_option_impact_score_{horizon}")) for horizon in HORIZONS)
    if presence <= 0:
        action = "no_intervention"
        reasons.append("no_visible_point_in_time_event")
    elif severity >= 0.75 or intensity >= 0.85:
        action = "block_new_entry"
        reasons.append("high_residual_event_risk")
    elif severity >= 0.55:
        action = "cap_new_exposure"
        reasons.append("moderate_residual_event_risk")
    elif severity >= 0.35 or option_impact >= 0.50:
        action = "warn"
        reasons.append("residual_event_warning")
    else:
        action = "no_intervention"
        reasons.append("residual_event_risk_below_intervention_threshold")
    if option_impact >= 0.50:
        reasons.append("option_expression_sensitive_event")
    if action in {"block_new_entry", "cap_new_exposure"} and option_impact >= 0.65:
        action = "reduce_or_flatten_review"
        reasons.append("option_sensitive_high_severity_review")
    return {
        "6_resolved_intervention_action": action,
        "6_resolved_intervention_severity_score": severity,
        "6_resolved_risk_horizon": risk_horizon,
        "6_resolved_reason_codes": sorted(set(reasons)),
    }


def _future_packet_eligibility(policy: Mapping[str, Any], diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    visible_count = int(diagnostics.get("visible_event_count") or 0)
    canonical_count = int(diagnostics.get("canonical_event_count") or 0)
    severity = _float(policy.get("6_resolved_intervention_severity_score"))
    eligible = visible_count > 0 and canonical_count > 0 and severity >= 0.35
    return {
        "eligible_for_future_event_family_packet": eligible,
        "eligibility_reason_codes": (
            ["canonical_residual_event_with_material_intervention_score"]
            if eligible
            else ["insufficient_residual_event_packet_evidence"]
        ),
    }


def _governed_decision_context(row: Mapping[str, Any]) -> dict[str, Any]:
    direct_intent = row.get("direct_underlying_intent") if isinstance(row.get("direct_underlying_intent"), Mapping) else {}
    option_plan = row.get("option_expression_plan") if isinstance(row.get("option_expression_plan"), Mapping) else {}
    return {
        "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
        "option_expression_plan_ref": row.get("option_expression_plan_ref"),
        "direct_underlying_action_type": direct_intent.get("underlying_action_type")
        or direct_intent.get("planned_underlying_action_type")
        or row.get("4_resolved_underlying_action_type"),
        "direct_underlying_action_side": direct_intent.get("action_side") or row.get("4_resolved_action_side"),
        "option_expression_type": option_plan.get("selected_expression_type") or row.get("5_resolved_expression_type"),
        "option_surface_status": option_plan.get("option_surface_status") or row.get("5_resolved_option_surface_status"),
    }


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _validate_no_forbidden_output(value: Any, path: str = "output") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden M06 output field at {path}.{key}: {key}")
            _validate_no_forbidden_output(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_no_forbidden_output(nested, f"{path}[{index}]")

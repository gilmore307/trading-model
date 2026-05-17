"""Deterministic EventFailureRiskModel V1 scaffold.

Layer 4 converts agent-reviewed event/strategy-failure gates into a
point-in-time ``event_failure_risk_vector``. It is intentionally conservative:
without a reviewed gate it emits an auditable no-risk/observe-only row, not raw
news alpha or automatic event-family promotion.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION, RESOLVED_STATUSES

ET = ZoneInfo("America/New_York")


def generate_rows(input_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [dict(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 4 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    gate = _payload(row, "event_strategy_failure_gate") or _payload(row, "event_strategy_failure_gate_v1")
    evidence = _payload(row, "event_failure_evidence_packet") or _payload(row, "event_failure_evidence")
    market = _payload(row, "market_context_state")
    sector = _payload(row, "sector_context_state")
    target = _payload(row, "target_context_state") or _payload(row, "target_state_vector")

    vector: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {"horizon_reason_codes": {}}
    reviewed = _review_accepted(gate)
    for horizon in HORIZONS:
        suffix = _suffix(horizon)
        scores = _scores(horizon, gate, evidence, market, sector, target, reviewed=reviewed)
        vector.update({
            f"4_event_strategy_failure_risk_score_{suffix}": scores["failure_risk"],
            f"4_event_entry_block_pressure_score_{suffix}": scores["entry_block"],
            f"4_event_exposure_cap_pressure_score_{suffix}": scores["exposure_cap"],
            f"4_event_strategy_disable_pressure_score_{suffix}": scores["strategy_disable"],
            f"4_event_path_risk_amplifier_score_{suffix}": scores["path_risk"],
            f"4_event_evidence_quality_score_{suffix}": scores["evidence_quality"],
            f"4_event_applicability_confidence_score_{suffix}": scores["applicability"],
        })
        diagnostics["horizon_reason_codes"][horizon] = scores["reason_codes"]

    resolved_status = _resolved_status(vector, reviewed=reviewed)
    ref = _stable_id("efrv", target_candidate_id, available_time, model_version)
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
        "event_strategy_failure_gate_ref": row.get("event_strategy_failure_gate_ref"),
        "event_failure_evidence_packet_ref": row.get("event_failure_evidence_packet_ref"),
        "event_failure_risk_vector_ref": ref,
        "4_resolved_event_failure_risk_status": resolved_status,
        **vector,
        "event_failure_risk_vector": vector,
        "event_failure_risk_diagnostics": diagnostics,
    }
    _validate_no_forbidden_output(output)
    return output


def _scores(horizon: str, gate: Mapping[str, Any], evidence: Mapping[str, Any], market: Mapping[str, Any], sector: Mapping[str, Any], target: Mapping[str, Any], *, reviewed: bool) -> dict[str, Any]:
    suffix = _suffix(horizon)
    if not reviewed:
        return {
            "failure_risk": 0.0,
            "entry_block": 0.0,
            "exposure_cap": 0.0,
            "strategy_disable": 0.0,
            "path_risk": 0.0,
            "evidence_quality": 0.0,
            "applicability": 0.0,
            "reason_codes": ["no_reviewed_event_failure_risk"],
        }
    evidence_quality = _score(gate, f"evidence_quality_score_{suffix}", "evidence_quality_score", default=_score(evidence, "evidence_quality_score", default=0.6))
    applicability = _score(gate, f"applicability_confidence_score_{suffix}", "applicability_confidence_score", default=_score(evidence, "applicability_confidence_score", default=0.55))
    effect = _score(gate, f"strategy_failure_effect_score_{suffix}", "strategy_failure_effect_score", "failure_effect_score", default=0.5)
    path = _score(gate, f"path_risk_amplifier_score_{suffix}", "path_risk_amplifier_score", default=effect)
    entry = _score(gate, f"entry_block_pressure_score_{suffix}", "entry_block_pressure_score", default=max(effect - 0.1, 0.0))
    exposure = _score(gate, f"exposure_cap_pressure_score_{suffix}", "exposure_cap_pressure_score", default=max(effect - 0.2, 0.0))
    disable = _score(gate, f"strategy_disable_pressure_score_{suffix}", "strategy_disable_pressure_score", default=max(effect - 0.35, 0.0))
    state_quality = min(
        _score(market, "1_state_quality_score", default=0.75),
        _score(sector, "2_state_quality_score", default=0.75),
        _score(target, "3_state_quality_score", default=0.75),
    )
    confidence = evidence_quality * applicability * state_quality
    multiplier = 0.55 + 0.45 * confidence
    failure_risk = _clip01(effect * multiplier)
    reason_codes = ["reviewed_event_failure_gate_applied"]
    if evidence_quality < 0.5:
        reason_codes.append("low_evidence_quality")
    if applicability < 0.5:
        reason_codes.append("low_applicability_confidence")
    if failure_risk >= 0.7:
        reason_codes.append("high_event_failure_risk")
    return {
        "failure_risk": round(failure_risk, 6),
        "entry_block": round(_clip01(entry * multiplier), 6),
        "exposure_cap": round(_clip01(exposure * multiplier), 6),
        "strategy_disable": round(_clip01(disable * multiplier), 6),
        "path_risk": round(_clip01(path * multiplier), 6),
        "evidence_quality": round(evidence_quality, 6),
        "applicability": round(applicability, 6),
        "reason_codes": reason_codes,
    }


def _resolved_status(vector: Mapping[str, Any], *, reviewed: bool) -> str:
    if not reviewed:
        return "no_reviewed_event_failure_risk"
    max_entry = max(float(value) for key, value in vector.items() if key.startswith("4_event_entry_block_pressure_score_"))
    max_disable = max(float(value) for key, value in vector.items() if key.startswith("4_event_strategy_disable_pressure_score_"))
    max_cap = max(float(value) for key, value in vector.items() if key.startswith("4_event_exposure_cap_pressure_score_"))
    max_risk = max(float(value) for key, value in vector.items() if key.startswith("4_event_strategy_failure_risk_score_"))
    if max_disable >= 0.7:
        return "strategy_family_disable_recommended"
    if max_entry >= 0.65:
        return "entry_block_recommended"
    if max_cap >= 0.6:
        return "exposure_cap_recommended"
    if max_risk >= 0.45:
        return "alpha_conditioning_required"
    if max_risk > 0.0:
        return "observe_only"
    return "no_reviewed_event_failure_risk"


def _review_accepted(gate: Mapping[str, Any]) -> bool:
    decision = str(gate.get("agent_review_decision") or gate.get("review_decision") or "").strip().lower()
    status = str(gate.get("gate_status") or gate.get("status") or "").strip().lower()
    return decision in {"accept_layer_04_event_failure_risk_scope", "accepted", "approve", "approved"} or status in {"accepted", "reviewed_accepted"}


def _payload(row: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = row.get(key)
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _score(payload: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in payload and payload[key] is not None:
            try:
                return _clip01(float(payload[key]))
            except (TypeError, ValueError):
                continue
    return _clip01(default)


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("event_available_time") or row.get("tradeable_time"))


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _suffix(horizon: str) -> str:
    return horizon.replace("min", "min")


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _validate_no_forbidden_output(row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in FORBIDDEN_OUTPUT_FIELDS if _contains_key(row, field))
    if leaked:
        raise ValueError(f"Layer 4 forbidden output fields emitted: {', '.join(leaked)}")
    if str(row.get("4_resolved_event_failure_risk_status")) not in RESOLVED_STATUSES:
        raise ValueError("invalid Layer 4 resolved event failure risk status")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

"""AlphaConfidenceModel generator.

Layer 5 converts reviewed Layer 1/2/3 state plus Layer 4 event-failure-risk context into the
final trained after-cost ``alpha_confidence_vector``. Model generation requires
a trained Layer 5 after-cost alpha artifact; missing artifacts are a blocked
training state.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .contract import FORBIDDEN_OUTPUT_FIELDS, HORIZONS, MODEL_ID, MODEL_LAYER, MODEL_VERSION
from .training import score_after_cost_alpha

ET = ZoneInfo("America/New_York")


def generate_rows(
    input_rows: Iterable[Mapping[str, Any]],
    *,
    model_version: str = MODEL_VERSION,
    after_cost_alpha_model: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if after_cost_alpha_model is None:
        raise ValueError("Layer 5 generation requires trained Layer 5 after-cost alpha artifacts")
    rows = [_normalize_input_row(row) for row in input_rows]
    if not rows:
        raise ValueError("at least one Layer 5 input row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    return [_model_row(row, model_version=model_version, after_cost_alpha_model=after_cost_alpha_model) for row in rows]


def _model_row(row: Mapping[str, Any], *, model_version: str, after_cost_alpha_model: Mapping[str, Any]) -> dict[str, Any]:
    available_time = _iso(_row_time(row))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")

    final_payload: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {"horizon_reason_codes": {}}
    for horizon in HORIZONS:
        suffix = _suffix(horizon)
        score_payload = _score_with_after_cost_model(row, horizon=horizon, after_cost_alpha_model=after_cost_alpha_model)
        vector_values = _vector_values_from_after_cost_score(score_payload)
        final_payload.update(
            {
                f"5_alpha_direction_score_{suffix}": vector_values["alpha_direction"],
                f"5_alpha_strength_score_{suffix}": vector_values["alpha_strength"],
                f"5_expected_return_score_{suffix}": vector_values["expected_return"],
                f"5_alpha_confidence_score_{suffix}": vector_values["alpha_confidence"],
                f"5_after_cost_alpha_score_{suffix}": vector_values["after_cost_alpha"],
                f"5_signal_reliability_score_{suffix}": vector_values["signal_reliability"],
                f"5_path_quality_score_{suffix}": vector_values["path_quality"],
                f"5_reversal_risk_score_{suffix}": vector_values["reversal_risk"],
                f"5_drawdown_risk_score_{suffix}": vector_values["drawdown_risk"],
                f"5_alpha_tradability_score_{suffix}": vector_values["alpha_tradability"],
            }
        )
        diagnostics["horizon_reason_codes"][horizon] = vector_values["reason_codes"]
        diagnostics.setdefault("after_cost_alpha_score", {})[horizon] = score_payload

    ref = _stable_id("acv", target_candidate_id, available_time, model_version)
    output = {
        "available_time": available_time,
        "tradeable_time": tradeable_time,
        "target_candidate_id": target_candidate_id,
        "training_sample_scope": row.get("training_sample_scope") or "dense_minute_target_state",
        "model_id": MODEL_ID,
        "model_layer": MODEL_LAYER,
        "model_version": model_version,
        "market_context_state_ref": row.get("market_context_state_ref"),
        "sector_context_state_ref": row.get("sector_context_state_ref"),
        "target_context_state_ref": row.get("target_context_state_ref") or row.get("target_state_vector_ref"),
        "event_failure_risk_vector_ref": row.get("event_failure_risk_vector_ref"),
        "alpha_confidence_vector_ref": ref,
        **final_payload,
        "alpha_confidence_vector": final_payload,
        "alpha_confidence_diagnostics": diagnostics,
    }
    _validate_no_forbidden_output(output)
    return output


def _score_with_after_cost_model(row: Mapping[str, Any], *, horizon: str, after_cost_alpha_model: Mapping[str, Any]) -> dict[str, Any]:
    artifact = _artifact_for_horizon(after_cost_alpha_model, horizon)
    try:
        return score_after_cost_alpha(row, artifact, horizon=horizon)
    except ValueError as error:
        raise ValueError(f"invalid Layer 5 after-cost alpha model artifact for {horizon}: {error}") from error


def _artifact_for_horizon(after_cost_alpha_model: Mapping[str, Any], horizon: str) -> Mapping[str, Any]:
    artifacts = after_cost_alpha_model.get("artifacts_by_horizon")
    if isinstance(artifacts, Mapping):
        artifact = artifacts.get(horizon)
        if isinstance(artifact, Mapping):
            return artifact
        raise ValueError(f"Layer 5 after-cost alpha artifact bundle is missing horizon {horizon!r}")
    if str(after_cost_alpha_model.get("horizon") or "") == horizon:
        return after_cost_alpha_model
    raise ValueError(f"Layer 5 after-cost alpha artifact is missing horizon {horizon!r}")


def _vector_values_from_after_cost_score(score_payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_score = _safe_float(score_payload.get("score"))
    raw_signed_edge = _safe_float(score_payload.get("signed_edge_score"))
    raw_coverage = _safe_float(score_payload.get("feature_coverage_score"))
    score = _clip01(raw_score if raw_score is not None else 0.5)
    signed_edge = _clip_signed(raw_signed_edge if raw_signed_edge is not None else (score - 0.5) * 2.0)
    coverage = _clip01(raw_coverage if raw_coverage is not None else 0.0)
    abs_edge = abs(signed_edge)
    uncertainty = 1.0 - coverage
    path_quality = _clip01(0.50 + 0.35 * abs_edge + 0.15 * (coverage - 0.50))
    reversal_risk = _clip01(0.50 - 0.25 * abs_edge + 0.25 * uncertainty)
    drawdown_risk = _clip01(0.50 - 0.20 * abs_edge + 0.30 * uncertainty)
    reason_codes = ["trained_after_cost_alpha_score"]
    if abs_edge < 0.05:
        reason_codes.append("no_material_alpha_edge")
    if coverage < 0.50:
        reason_codes.append("low_feature_coverage")
    return {
        "alpha_direction": round(signed_edge, 6),
        "alpha_strength": round(abs_edge, 6),
        "expected_return": round(signed_edge, 6),
        "alpha_confidence": round(score, 6),
        "after_cost_alpha": round(score, 6),
        "signal_reliability": round(coverage, 6),
        "path_quality": round(path_quality, 6),
        "reversal_risk": round(reversal_risk, 6),
        "drawdown_risk": round(drawdown_risk, 6),
        "alpha_tradability": round(_clip01(abs_edge * coverage), 6),
        "reason_codes": reason_codes,
    }


def _normalize_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in ("market_context_state", "sector_context_state", "target_context_state", "target_state_vector", "event_failure_risk_vector", "quality_calibration_state"):
        output[key] = _coerce_payload(output.get(key))
    return output


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

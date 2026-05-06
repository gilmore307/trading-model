"""Deterministic TargetStateVectorModel V1 generator.

Consumes point-in-time ``feature_03_target_state_vector`` rows and emits the
accepted Layer 3 target_context_state model output shape. The generator keeps signed current target
direction separate from direction-neutral tradability, transition/noise risk,
liquidity, and state quality. It does not output alpha confidence, position
size, strategy/action variants, option contracts, or execution instructions.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MODEL_ID = "target_state_vector_model"
MODEL_VERSION = "target_context_state_v1_contract"
PRIMARY_TABLE = "model_03_target_state_vector"
STATE_WINDOWS = ("5min", "15min", "60min", "390min")
JSON_BLOCKS = ("market_state_features", "sector_state_features", "target_state_features", "cross_state_features")
FORBIDDEN_OUTPUT_FIELDS = {"ticker", "symbol", "company", "strategy_variant", "alpha_confidence", "position_size", "option_contract_id", "final_action"}


def generate_rows(feature_rows: Iterable[Mapping[str, Any]], *, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    rows = [_normalize_feature_row(row) for row in feature_rows]
    if not rows:
        raise ValueError("at least one feature_03_target_state_vector row is required")
    rows.sort(key=lambda row: (_row_time(row), str(row.get("target_candidate_id") or "")))
    output = [_model_row(row, model_version=model_version) for row in rows]
    return output


def _model_row(row: Mapping[str, Any], *, model_version: str) -> dict[str, Any]:
    target = _payload(row, "target_state_features")
    market = _payload(row, "market_state_features")
    sector = _payload(row, "sector_state_features")
    cross = _payload(row, "cross_state_features")
    available_time = _iso(_row_time(row))
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    if not target_candidate_id:
        raise ValueError("target_candidate_id is required")
    target_context_state_ref = _stable_id("tcs", target_candidate_id, available_time, model_version)
    score_payload = _score_payload(target, market, sector, cross)
    diagnostics = _diagnostics(row, target, market, sector, cross, score_payload)
    output = {
        "available_time": available_time,
        "tradeable_time": _iso(_parse_time(row.get("tradeable_time") or available_time)),
        "target_candidate_id": target_candidate_id,
        "model_id": MODEL_ID,
        "model_version": model_version,
        "market_context_state_ref": row.get("market_context_state_ref"),
        "sector_context_state_ref": row.get("sector_context_state_ref"),
        "target_context_state_ref": target_context_state_ref,
        **score_payload,
        "target_context_state": {
            "market_state_features": market,
            "sector_state_features": sector,
            "target_state_features": target,
            "cross_state_features": cross,
            "score_payload": score_payload,
        },
        "target_state_embedding": _embedding(score_payload),
        "state_cluster_id": _cluster_id(score_payload),
        "state_quality_diagnostics": diagnostics,
    }
    forbidden = sorted(FORBIDDEN_OUTPUT_FIELDS & set(output))
    if forbidden:
        raise ValueError(f"forbidden Layer 3 output fields: {forbidden}")
    return output


def _score_payload(target: Mapping[str, Any], market: Mapping[str, Any], sector: Mapping[str, Any], cross: Mapping[str, Any]) -> dict[str, Any]:
    liquidity = _liquidity_score(target)
    state_quality = _quality_score(target, market, sector, cross)
    payload: dict[str, Any] = {
        "3_target_liquidity_tradability_score": liquidity,
        "3_state_quality_score": state_quality,
        "3_evidence_count": _evidence_count(target, market, sector, cross),
    }
    for window in STATE_WINDOWS:
        suffix = _suffix(window)
        direction = _return_for_window(target, window)
        direction_score = _bounded(direction, scale=0.05)
        direction_strength = None if direction_score is None else abs(direction_score)
        trend_quality = _trend_quality(target, window, direction)
        stability = _path_stability(target, window)
        noise = 1.0 - stability if stability is not None else None
        transition_risk = _transition_risk(target, cross, window, noise)
        persistence = _state_persistence(target, window)
        exhaustion_risk = _exhaustion_risk(target, window)
        alignment = _context_alignment(cross, direction)
        support = _context_support(cross, market, sector, direction)
        tradability = _geometric_score([
            direction_strength,
            trend_quality,
            stability,
            liquidity,
            support,
            _invert01(noise),
            _invert01(transition_risk),
            persistence,
            _invert01(exhaustion_risk),
            state_quality,
        ])
        payload.update({
            f"3_target_direction_score_{suffix}": direction_score,
            f"3_target_direction_strength_score_{suffix}": direction_strength,
            f"3_target_trend_quality_score_{suffix}": trend_quality,
            f"3_target_path_stability_score_{suffix}": stability,
            f"3_target_noise_score_{suffix}": noise,
            f"3_target_transition_risk_score_{suffix}": transition_risk,
            f"3_target_state_persistence_score_{suffix}": persistence,
            f"3_target_exhaustion_risk_score_{suffix}": exhaustion_risk,
            f"3_context_direction_alignment_score_{suffix}": alignment,
            f"3_context_support_quality_score_{suffix}": support,
            f"3_tradability_score_{suffix}": tradability,
        })
    return payload


def _normalize_feature_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for block in JSON_BLOCKS:
        output[block] = _coerce_payload(output.get(block))
    return output


def _payload(row: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = _coerce_payload(row.get(key))
    if not isinstance(value, Mapping):
        return {}
    if _contains_forbidden_identity(value):
        raise ValueError(f"{key} contains model-facing identity or forbidden downstream fields")
    return value


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


def _contains_forbidden_identity(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_OUTPUT_FIELDS or key_l in {"ticker", "symbol", "company", "audit_symbol_ref", "routing_symbol_ref"}:
                return True
            if _contains_forbidden_identity(nested):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_identity(item) for item in value)
    return False


def _return_for_window(target: Mapping[str, Any], window: str) -> float | None:
    shape = target.get("target_direction_return_shape")
    if isinstance(shape, Mapping):
        return _safe_float(shape.get(f"return_{window}"))
    return None


def _trend_quality(target: Mapping[str, Any], window: str, direction: float | None) -> float | None:
    state = target.get("target_trend_quality_state")
    if isinstance(state, Mapping):
        explicit = _safe_float(state.get(f"trend_quality_{window}") or state.get("trend_quality_score"))
        if explicit is not None:
            return _clip01(explicit)
    if direction is None:
        return None
    return _clip01(abs(math.tanh(direction / 0.03)))


def _path_stability(target: Mapping[str, Any], window: str) -> float | None:
    trend_state = target.get("target_trend_quality_state")
    if isinstance(trend_state, Mapping):
        explicit = _safe_float(trend_state.get(f"path_stability_{window}") or trend_state.get("path_stability_score"))
        if explicit is not None:
            return _clip01(explicit)
    volatility_state = target.get("target_volatility_range_state")
    vol = None
    if isinstance(volatility_state, Mapping):
        vol = _safe_float(volatility_state.get(f"realized_vol_{window}") or volatility_state.get("realized_volatility"))
    if vol is None:
        returns = target.get("target_direction_return_shape")
        if isinstance(returns, Mapping):
            values = [_safe_float(value) for key, value in returns.items() if str(key).startswith("return_")]
            clean = [abs(value) for value in values if value is not None]
            vol = pstdev(clean) if len(clean) > 1 else None
    if vol is None:
        return None
    return _clip01(1.0 - min(abs(vol) / 0.08, 1.0))


def _transition_risk(target: Mapping[str, Any], cross: Mapping[str, Any], window: str, noise: float | None) -> float | None:
    explicit = None
    transition = target.get("target_transition_risk_state")
    if isinstance(transition, Mapping):
        explicit = _safe_float(transition.get(f"transition_risk_{window}") or transition.get("transition_risk_score"))
    if explicit is not None:
        return _clip01(explicit)
    residual = abs(_safe_float(cross.get("idiosyncratic_residual_state")) or 0.0)
    parts = [noise, min(residual / 0.08, 1.0) if residual else None, _exhaustion_risk(target, window)]
    return _average(parts)


def _state_persistence(target: Mapping[str, Any], window: str) -> float | None:
    state = target.get("target_trend_age_state")
    if not isinstance(state, Mapping):
        return None
    explicit = _safe_float(state.get(f"state_persistence_score_{window}") or state.get("state_persistence_score"))
    return _clip01(explicit)


def _exhaustion_risk(target: Mapping[str, Any], window: str) -> float | None:
    state = target.get("target_exhaustion_decay_state")
    if not isinstance(state, Mapping):
        return None
    explicit = _safe_float(state.get(f"late_trend_risk_score_{window}") or state.get("late_trend_risk_score"))
    return _clip01(explicit)


def _liquidity_score(target: Mapping[str, Any]) -> float | None:
    liquidity = target.get("target_liquidity_tradability_state")
    if not isinstance(liquidity, Mapping):
        return None
    explicit = _safe_float(liquidity.get("liquidity_tradability_score"))
    if explicit is not None:
        return _clip01(explicit)
    spread = _safe_float(liquidity.get("spread_bps"))
    dollar_volume = _safe_float(liquidity.get("dollar_volume"))
    spread_score = None if spread is None else _clip01(1.0 - min(spread / 100.0, 1.0))
    volume_score = None if dollar_volume is None else _clip01(math.log10(max(dollar_volume, 1.0)) / 8.0)
    return _average([spread_score, volume_score])


def _context_alignment(cross: Mapping[str, Any], direction: float | None) -> float | None:
    if direction is None:
        return None
    sector_residual = _safe_float(cross.get("target_vs_sector_residual_direction"))
    market_residual = _safe_float(cross.get("target_vs_market_residual_direction"))
    confirmation = str(cross.get("sector_confirmation_state") or "").lower()
    base = 1.0 if confirmation == "sector_confirmed" else -0.5 if confirmation == "sector_divergent" else 0.0
    residual_penalty = _average([abs(sector_residual) if sector_residual is not None else None, abs(market_residual) if market_residual is not None else None])
    if residual_penalty is not None:
        base -= min(residual_penalty / 0.10, 1.0) * 0.25
    return max(-1.0, min(1.0, base))


def _context_support(cross: Mapping[str, Any], market: Mapping[str, Any], sector: Mapping[str, Any], direction: float | None) -> float | None:
    alignment = _context_alignment(cross, direction)
    if alignment is not None:
        return _clip01((alignment + 1.0) / 2.0)
    return _average([_generic_quality(market), _generic_quality(sector)])


def _quality_score(*blocks: Mapping[str, Any]) -> float:
    present = sum(1 for block in blocks if block)
    sync_ok = all(_sync_policy_ok(block) for block in blocks if block)
    return _clip01((present / max(len(blocks), 1)) * (1.0 if sync_ok else 0.5)) or 0.0


def _evidence_count(*blocks: Mapping[str, Any]) -> int:
    def count(value: Any) -> int:
        if isinstance(value, Mapping):
            return sum(count(nested) for nested in value.values())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return sum(count(item) for item in value)
        return 1 if _safe_float(value) is not None or (isinstance(value, str) and value) else 0
    return sum(count(block) for block in blocks)


def _diagnostics(row: Mapping[str, Any], target: Mapping[str, Any], market: Mapping[str, Any], sector: Mapping[str, Any], cross: Mapping[str, Any], scores: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "feature_quality_diagnostics": _coerce_payload(row.get("feature_quality_diagnostics")),
        "state_window_sync_policy": "market_sector_target_blocks_must_share_identical_observation_windows",
        "state_window_sync_ok": all(_sync_policy_ok(block) for block in (target, market, sector, cross) if block),
        "identity_leakage_check": "passed",
        "downstream_action_fields_present": sorted(FORBIDDEN_OUTPUT_FIELDS & set(row)),
        "score_fields_present": sorted(key for key, value in scores.items() if value is not None),
        "field_semantics_policy": {
            "direction_scores": "signed_direction_only_not_quality_or_size",
            "tradability_scores": "direction_neutral_high_is_good_path_and_execution_cleanliness",
            "risk_noise_scores": "direction_neutral_high_is_bad",
            "target_state_embedding": "research_only_not_primary_model_feature",
            "state_cluster_id": "research_only_not_primary_model_feature",
        },
    }


def _embedding(scores: Mapping[str, Any]) -> list[float]:
    keys = ["3_target_direction_score_15min", "3_target_direction_strength_score_15min", "3_target_trend_quality_score_15min", "3_target_path_stability_score_15min", "3_target_transition_risk_score_15min", "3_target_state_persistence_score_15min", "3_target_exhaustion_risk_score_15min", "3_target_liquidity_tradability_score", "3_context_support_quality_score_15min", "3_tradability_score_15min", "3_state_quality_score"]
    return [round(_safe_float(scores.get(key)) or 0.0, 8) for key in keys]


def _cluster_id(scores: Mapping[str, Any]) -> str:
    direction = _safe_float(scores.get("3_target_direction_score_15min")) or 0.0
    tradability = _safe_float(scores.get("3_tradability_score_15min")) or 0.0
    direction_bucket = "up" if direction > 0.2 else "down" if direction < -0.2 else "flat"
    tradability_bucket = "clean" if tradability >= 0.66 else "watch" if tradability >= 0.4 else "noisy"
    return f"target_state_{direction_bucket}_{tradability_bucket}"


def _generic_quality(block: Mapping[str, Any]) -> float | None:
    if not block:
        return None
    for key in ("state_quality_score", "data_quality_score", "coverage_score"):
        value = _safe_float(block.get(key))
        if value is not None:
            return _clip01(value)
    return 0.5


def _sync_policy_ok(block: Mapping[str, Any]) -> bool:
    policy = block.get("state_window_sync_policy")
    return policy in (None, "", "market_sector_target_blocks_must_share_identical_observation_windows")


def _row_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("snapshot_time") or row.get("timestamp"))


def _parse_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("time value is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _suffix(window: str) -> str:
    return window.replace("min", "min")


def _bounded(value: float | None, *, scale: float = 1.0) -> float | None:
    if value is None:
        return None
    return math.tanh(value / scale)


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _invert01(value: float | None) -> float | None:
    if value is None:
        return None
    return 1.0 - _clip01(value)


def _average(values: Iterable[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return mean(clean) if clean else None


def _geometric_score(values: Iterable[float | None]) -> float | None:
    clean = [_clip01(value) for value in values if value is not None]
    if not clean:
        return None
    # Multiplicative direction-neutral tradability: one badly failing component
    # should drag the state down more than a simple arithmetic average would.
    product = 1.0
    for value in clean:
        product *= max(value or 0.0, 1e-9)
    return product ** (1.0 / len(clean))


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"

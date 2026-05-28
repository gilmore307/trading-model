"""Training and inference helpers for Layer 5 after-cost alpha scoring."""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

from .contract import HORIZONS, MODEL_ID, MODEL_VERSION

ARTIFACT_SCHEMA_VERSION = "layer_05_after_cost_alpha_model_artifact"
MODEL_TYPE = "standardized_linear_after_cost_alpha"
DEFAULT_RETURN_SCALE = 0.02
DEFAULT_LEARNING_RATE = 0.08
DEFAULT_ITERATIONS = 700
DEFAULT_L2 = 0.001


FEATURE_TEMPLATES: tuple[str, ...] = (
    "1_market_direction_score",
    "1_market_direction_strength_score",
    "1_market_trend_quality_score",
    "1_market_stability_score",
    "1_market_transition_risk_score",
    "1_market_risk_stress_score",
    "1_market_liquidity_support_score",
    "1_state_quality_score",
    "2_sector_relative_direction_score",
    "2_sector_trend_quality_score",
    "2_sector_transition_risk_score",
    "2_sector_context_support_quality_score",
    "2_sector_internal_dispersion_score",
    "2_sector_crowding_risk_score",
    "2_sector_tradability_score",
    "2_state_quality_score",
    "3_target_direction_score_<horizon>",
    "3_target_trend_quality_score_<horizon>",
    "3_target_path_stability_score_<horizon>",
    "3_target_noise_score_<horizon>",
    "3_target_transition_risk_score_<horizon>",
    "3_context_direction_alignment_score_<horizon>",
    "3_context_support_quality_score_<horizon>",
    "3_tradability_score_<horizon>",
    "3_state_quality_score",
    "3_beta_dependency_score_<horizon>",
    "4_event_strategy_failure_risk_score_<horizon>",
    "4_event_entry_block_pressure_score_<horizon>",
    "4_event_exposure_cap_pressure_score_<horizon>",
    "4_event_strategy_disable_pressure_score_<horizon>",
    "4_event_path_risk_amplifier_score_<horizon>",
    "4_event_session_gap_risk_score_<horizon>",
    "4_event_evidence_quality_score_<horizon>",
    "4_event_applicability_confidence_score_<horizon>",
    "quality_sample_support_score",
    "quality_walk_forward_reliability_score",
    "quality_model_ensemble_agreement_score",
    "quality_model_disagreement_score",
    "quality_out_of_distribution_score",
    "quality_data_quality_score",
)


def train_after_cost_alpha_model(
    training_rows: Iterable[Mapping[str, Any]],
    *,
    horizon: str = "1W",
    label_field: str | None = None,
    return_scale: float = DEFAULT_RETURN_SCALE,
    iterations: int = DEFAULT_ITERATIONS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    l2: float = DEFAULT_L2,
    model_version: str = MODEL_VERSION,
) -> dict[str, Any]:
    """Train a small direct Layer 5 score model.

    The supervised target is the score itself: 0.5 means after-cost neutral,
    above 0.5 means positive after-cost edge, and below 0.5 means negative
    after-cost edge. This is deliberately not threshold fitting over an
    unrelated raw confidence score.
    """

    _validate_horizon(horizon)
    rows = [dict(row) for row in training_rows]
    samples: list[tuple[list[float], float]] = []
    feature_names = _feature_names(horizon)
    selected_label_field = label_field
    for row in rows:
        if selected_label_field is None:
            selected_label_field = _label_field(row, horizon)
        if not selected_label_field:
            continue
        realized_return = _safe_float(row.get(selected_label_field))
        if realized_return is None:
            continue
        features = extract_after_cost_features(row, horizon=horizon, feature_names=feature_names)
        samples.append((features, _return_to_score(realized_return, return_scale=return_scale)))
    if not samples:
        raise ValueError("at least one labeled Layer 5 training row is required")

    means, scales = _standardization([features for features, _target in samples])
    standardized = [(_standardize(features, means, scales), target) for features, target in samples]
    weights = [0.0 for _name in feature_names]
    bias = _logit(_clip_target(sum(target for _features, target in standardized) / len(standardized)))
    for _step in range(max(1, iterations)):
        grad_w = [0.0 for _name in feature_names]
        grad_b = 0.0
        for features, target in standardized:
            prediction = _sigmoid(bias + sum(weight * value for weight, value in zip(weights, features)))
            error = prediction - target
            grad_b += error
            for index, value in enumerate(features):
                grad_w[index] += error * value
        count = float(len(standardized))
        bias -= learning_rate * grad_b / count
        for index, weight in enumerate(weights):
            regularized = grad_w[index] / count + l2 * weight
            weights[index] = weight - learning_rate * regularized

    predictions = [_sigmoid(bias + sum(weight * value for weight, value in zip(weights, features))) for features, _target in standardized]
    targets = [target for _features, target in standardized]
    mae = sum(abs(prediction - target) for prediction, target in zip(predictions, targets)) / len(targets)
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "model_id": MODEL_ID,
        "model_version": model_version,
        "model_type": MODEL_TYPE,
        "score_semantics": "0.5_after_cost_neutral__above_positive_edge__below_negative_edge",
        "horizon": horizon,
        "label_field": selected_label_field,
        "return_scale": return_scale,
        "feature_names": feature_names,
        "feature_means": means,
        "feature_scales": scales,
        "weights": [round(weight, 12) for weight in weights],
        "bias": round(bias, 12),
        "training_summary": {
            "sample_count": len(samples),
            "iterations": max(1, iterations),
            "learning_rate": learning_rate,
            "l2": l2,
            "mean_target_score": round(sum(targets) / len(targets), 8),
            "mean_absolute_error": round(mae, 8),
        },
    }


def score_after_cost_alpha(row: Mapping[str, Any], artifact: Mapping[str, Any], *, horizon: str) -> dict[str, Any]:
    """Score one Layer 5 input row with a trained after-cost alpha artifact."""

    _validate_artifact(artifact)
    artifact_horizon = str(artifact.get("horizon") or horizon)
    _validate_horizon(artifact_horizon)
    feature_names = [str(name) for name in artifact["feature_names"]]
    features = extract_after_cost_features(row, horizon=artifact_horizon, feature_names=feature_names)
    means = [float(value) for value in artifact["feature_means"]]
    scales = [float(value) for value in artifact["feature_scales"]]
    weights = [float(value) for value in artifact["weights"]]
    standardized = _standardize(features, means, scales)
    raw_logit = float(artifact["bias"]) + sum(weight * value for weight, value in zip(weights, standardized))
    score = _sigmoid(raw_logit)
    coverage = sum(1 for value in features if value != 0.0) / len(features) if features else 0.0
    return {
        "score": round(score, 6),
        "signed_edge_score": round((score - 0.5) * 2.0, 6),
        "raw_logit": round(raw_logit, 6),
        "feature_coverage_score": round(coverage, 6),
        "model_type": str(artifact.get("model_type")),
        "score_semantics": str(artifact.get("score_semantics")),
        "artifact_horizon": artifact_horizon,
    }


def extract_after_cost_features(row: Mapping[str, Any], *, horizon: str, feature_names: Sequence[str] | None = None) -> list[float]:
    names = list(feature_names) if feature_names is not None else _feature_names(horizon)
    market = _mapping(row.get("market_context_state"))
    sector = _mapping(row.get("sector_context_state"))
    target = _mapping(row.get("target_context_state") or row.get("target_state_vector"))
    event = _mapping(row.get("event_failure_risk_vector"))
    quality = _mapping(row.get("quality_calibration_state"))
    payloads = {
        "1_": market,
        "2_": sector,
        "3_": target,
        "4_": event,
        "quality_": quality,
    }
    values: list[float] = []
    for name in names:
        if name.startswith("quality_"):
            key = name.removeprefix("quality_")
            values.append(_score(quality, key, default=0.0))
            continue
        value = None
        for prefix, payload in payloads.items():
            if name.startswith(prefix):
                value = payload.get(name)
                break
        values.append(_safe_feature(value))
    return values


def _feature_names(horizon: str) -> list[str]:
    _validate_horizon(horizon)
    return [template.replace("<horizon>", horizon) for template in FEATURE_TEMPLATES]


def _label_field(row: Mapping[str, Any], horizon: str) -> str | None:
    candidates = (
        f"after_cost_return_{horizon}",
        f"realized_after_cost_return_{horizon}",
        f"net_return_{horizon}",
        f"idiosyncratic_residual_return_{horizon}",
        f"forward_return_{horizon}",
        "after_cost_return",
        "realized_after_cost_return",
        "net_return",
    )
    for candidate in candidates:
        if _safe_float(row.get(candidate)) is not None:
            return candidate
    return None


def _validate_horizon(horizon: str) -> None:
    if horizon not in HORIZONS:
        raise ValueError(f"unsupported Layer 5 horizon: {horizon!r}")


def _validate_artifact(artifact: Mapping[str, Any]) -> None:
    if artifact.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("unsupported Layer 5 after-cost alpha model artifact schema")
    required = ("feature_names", "feature_means", "feature_scales", "weights", "bias")
    missing = [field for field in required if field not in artifact]
    if missing:
        raise ValueError(f"Layer 5 after-cost alpha model artifact missing fields: {', '.join(missing)}")
    lengths = {len(artifact["feature_names"]), len(artifact["feature_means"]), len(artifact["feature_scales"]), len(artifact["weights"])}
    if len(lengths) != 1:
        raise ValueError("Layer 5 after-cost alpha model artifact vector lengths do not match")


def _standardization(samples: Sequence[Sequence[float]]) -> tuple[list[float], list[float]]:
    means: list[float] = []
    scales: list[float] = []
    width = len(samples[0]) if samples else 0
    for index in range(width):
        column = [sample[index] for sample in samples]
        mean = sum(column) / len(column)
        variance = sum((value - mean) ** 2 for value in column) / len(column)
        means.append(mean)
        scales.append(max(math.sqrt(variance), 1e-6))
    return means, scales


def _standardize(features: Sequence[float], means: Sequence[float], scales: Sequence[float]) -> list[float]:
    return [(value - mean) / scale for value, mean, scale in zip(features, means, scales)]


def _return_to_score(realized_return: float, *, return_scale: float) -> float:
    scale = max(abs(return_scale), 1e-9)
    return _clip01(0.5 + 0.5 * math.tanh(realized_return / scale))


def _clip_target(value: float) -> float:
    return max(1e-6, min(1.0 - 1e-6, value))


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _logit(value: float) -> float:
    clipped = _clip_target(value)
    return math.log(clipped / (1.0 - clipped))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_feature(value: Any) -> float:
    parsed = _safe_float(value)
    if parsed is None:
        return 0.0
    return max(-1.0, min(1.0, parsed))


def _score(mapping: Mapping[str, Any], key: str, *, default: float) -> float:
    value = _safe_float(mapping.get(key))
    if value is None:
        return default
    return max(0.0, min(1.0, value))


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

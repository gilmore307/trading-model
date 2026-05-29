"""Shared LightGBM score-model artifact mechanics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

_BOOSTER_CACHE: dict[int, tuple[str, Any]] = {}


@dataclass(frozen=True)
class LightGBMScoreModelSpec:
    """Layer-owned artifact identity and training defaults."""

    schema_version: str
    model_id: str
    model_version: str
    model_type: str
    score_semantics: str
    seed: int
    objective: str = "regression"
    metric: str = "l1"
    boosting_type: str = "gbdt"
    learning_rate: float = 0.08
    iterations: int = 700
    l2: float = 0.001


def train_lightgbm_score_model(
    *,
    spec: LightGBMScoreModelSpec,
    feature_rows: Sequence[Sequence[float]],
    targets: Sequence[float],
    feature_names: Sequence[str],
    artifact_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Train and serialize a deterministic LightGBM score artifact."""

    if not feature_rows or not targets:
        raise ValueError("at least one labeled training row is required")
    if len(feature_rows) != len(targets):
        raise ValueError("feature row count must match target count")
    if any(len(row) != len(feature_names) for row in feature_rows):
        raise ValueError("every feature row must match feature_names")

    lgb = _load_lightgbm()
    np = _load_numpy()
    features = np.asarray(feature_rows, dtype=float)
    target_values = np.asarray(targets, dtype=float)
    params = {
        "objective": spec.objective,
        "metric": spec.metric,
        "boosting_type": spec.boosting_type,
        "learning_rate": spec.learning_rate,
        "lambda_l2": spec.l2,
        "num_leaves": min(31, max(2, len(feature_rows))),
        "min_data_in_leaf": 1,
        "min_data_in_bin": 1,
        "feature_pre_filter": False,
        "verbosity": -1,
        "seed": spec.seed,
        "feature_fraction_seed": spec.seed,
        "bagging_seed": spec.seed,
        "data_random_seed": spec.seed,
        "deterministic": True,
        "force_col_wise": True,
    }
    dataset = lgb.Dataset(features, label=target_values, feature_name=list(feature_names), free_raw_data=False)
    booster = lgb.train(params, dataset, num_boost_round=max(1, spec.iterations))
    predictions = [_clip01(float(value)) for value in booster.predict(features)]
    mae = sum(abs(prediction - target) for prediction, target in zip(predictions, target_values)) / len(target_values)
    artifact = {
        "schema_version": spec.schema_version,
        "model_id": spec.model_id,
        "model_version": spec.model_version,
        "model_type": spec.model_type,
        "score_semantics": spec.score_semantics,
        "feature_names": list(feature_names),
        "booster_model": booster.model_to_string(),
        "booster_params": params,
        "training_summary": {
            "sample_count": len(feature_rows),
            "boosting_rounds": max(1, spec.iterations),
            "learning_rate": spec.learning_rate,
            "l2": spec.l2,
            "mean_target_score": round(float(sum(target_values) / len(target_values)), 8),
            "mean_absolute_error": round(mae, 8),
        },
    }
    if artifact_fields:
        artifact.update(dict(artifact_fields))
    return artifact


def predict_lightgbm_score(features: Sequence[float], artifact: Mapping[str, Any]) -> float:
    """Run one point-in-time feature row through a serialized LightGBM score artifact."""

    validate_lightgbm_score_artifact(artifact)
    np = _load_numpy()
    expected_width = len(artifact["feature_names"])
    if len(features) != expected_width:
        raise ValueError(f"feature count {len(features)} does not match artifact width {expected_width}")
    booster = _booster_for_artifact(artifact)
    return float(booster.predict(np.asarray([features], dtype=float))[0])


def validate_lightgbm_score_artifact(
    artifact: Mapping[str, Any],
    *,
    schema_version: str | None = None,
    model_type: str | None = None,
) -> None:
    """Validate the shared artifact shape plus optional layer-owned identity fields."""

    required = ("schema_version", "model_id", "model_version", "model_type", "feature_names", "booster_model")
    missing = [field for field in required if field not in artifact]
    if missing:
        raise ValueError(f"LightGBM score artifact missing fields: {', '.join(missing)}")
    feature_names = artifact.get("feature_names")
    if not isinstance(feature_names, Sequence) or isinstance(feature_names, (str, bytes)) or not feature_names:
        raise ValueError("LightGBM score artifact feature_names must be a non-empty sequence")
    if schema_version is not None and artifact.get("schema_version") != schema_version:
        raise ValueError("unsupported LightGBM score artifact schema")
    if model_type is not None and artifact.get("model_type") != model_type:
        raise ValueError(f"unsupported LightGBM score artifact model type: {artifact.get('model_type')!r}")


def _load_lightgbm() -> Any:
    try:
        import lightgbm as lgb  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:  # pragma: no cover - exercised only in minimal environments
        raise RuntimeError("LightGBM is required for model training and inference; install requirements.txt") from error
    return lgb


def _booster_for_artifact(artifact: Mapping[str, Any]) -> Any:
    model = str(artifact["booster_model"])
    cache_key = id(artifact)
    cached = _BOOSTER_CACHE.get(cache_key)
    if cached is not None and cached[0] == model:
        return cached[1]
    booster = _load_lightgbm().Booster(model_str=model)
    _BOOSTER_CACHE[cache_key] = (model, booster)
    return booster


def _load_numpy() -> Any:
    try:
        import numpy as np  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:  # pragma: no cover - LightGBM requires numpy in normal installs
        raise RuntimeError("NumPy is required for model training and inference; install requirements.txt") from error
    return np


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))

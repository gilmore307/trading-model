"""Small dependency-light continual residual MLP learner helpers."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DatasetSplit:
    """Named row indexes for a chronological evaluation split."""

    name: str
    fold_keys: tuple[str, ...]
    indexes: tuple[int, ...]


def chronological_month_splits(
    fold_keys: Sequence[str],
    *,
    train_months: int = 4,
    validation_months: int = 1,
) -> list[DatasetSplit]:
    """Build train/validation/test splits from chronological month keys."""

    months = tuple(sorted(dict.fromkeys(str(key) for key in fold_keys)))
    if len(months) < train_months + validation_months:
        raise ValueError("not enough chronological months for the requested split policy")
    split_defs = (
        ("train", months[:train_months]),
        ("validation", months[train_months : train_months + validation_months]),
        ("test", months[train_months + validation_months :]),
    )
    splits: list[DatasetSplit] = []
    for name, split_months in split_defs:
        indexes = tuple(index for index, key in enumerate(fold_keys) if key in split_months)
        splits.append(DatasetSplit(name=name, fold_keys=tuple(split_months), indexes=indexes))
    return splits


def standardize_by_train(
    feature_rows: Sequence[Sequence[float]],
    train_indexes: Sequence[int],
) -> tuple[list[list[float]], dict[str, Any]]:
    """Standardize rows using only train indexes."""

    np = _load_numpy()
    features = np.asarray(feature_rows, dtype=float)
    if features.ndim != 2 or features.shape[0] == 0 or features.shape[1] == 0:
        raise ValueError("feature_rows must be a non-empty 2D matrix")
    if not train_indexes:
        raise ValueError("train_indexes must not be empty")
    train = features[list(train_indexes), :]
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    scaled = (features - mean) / std
    return scaled.tolist(), {"mean": mean.tolist(), "std": std.tolist()}


def train_mlp_regressor(
    *,
    feature_rows: Sequence[Sequence[float]],
    targets: Sequence[float],
    train_indexes: Sequence[int],
    hidden_units: int = 12,
    epochs: int = 450,
    learning_rate: float = 0.015,
    l2: float = 0.0005,
    seed: int = 23,
) -> dict[str, Any]:
    """Train the current dependency-light continual residual MLP implementation."""

    np = _load_numpy()
    x = np.asarray(feature_rows, dtype=float)
    y = np.asarray(targets, dtype=float)
    _validate_xy(x, y)
    rng = np.random.default_rng(seed)
    width = x.shape[1]
    hidden = max(1, int(hidden_units))
    w1 = rng.normal(0.0, 0.08, size=(width, hidden))
    b1 = np.zeros(hidden)
    w2 = rng.normal(0.0, 0.08, size=hidden)
    b2 = 0.0
    train = tuple(int(index) for index in train_indexes)
    for _epoch in range(max(1, epochs)):
        for index in train:
            row = x[index]
            target = y[index]
            z1 = row @ w1 + b1
            h = np.tanh(z1)
            prediction = _sigmoid(float(h @ w2 + b2))
            error = prediction - target
            out_grad = error * prediction * (1.0 - prediction)
            grad_w2 = out_grad * h + l2 * w2
            grad_b2 = out_grad
            hidden_grad = (out_grad * w2) * (1.0 - h * h)
            grad_w1 = np.outer(row, hidden_grad) + l2 * w1
            grad_b1 = hidden_grad
            w2 -= learning_rate * grad_w2
            b2 -= learning_rate * grad_b2
            w1 -= learning_rate * grad_w1
            b1 -= learning_rate * grad_b1
    return {
        "model_type": "continual_residual_mlp_sgd",
        "seed": seed,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "l2": l2,
        "hidden_units": hidden,
        "w1": w1.tolist(),
        "b1": b1.tolist(),
        "w2": w2.tolist(),
        "b2": b2,
    }


def predict_mlp(feature_rows: Sequence[Sequence[float]], artifact: Mapping[str, Any]) -> list[float]:
    """Predict with a one-hidden-layer MLP artifact."""

    np = _load_numpy()
    x = np.asarray(feature_rows, dtype=float)
    w1 = np.asarray(artifact["w1"], dtype=float)
    b1 = np.asarray(artifact["b1"], dtype=float)
    w2 = np.asarray(artifact["w2"], dtype=float)
    b2 = float(artifact["b2"])
    hidden = np.tanh(x @ w1 + b1)
    raw = hidden @ w2 + b2
    return [_sigmoid(float(value)) for value in raw]


def regression_metrics(targets: Sequence[float], predictions: Sequence[float]) -> dict[str, Any]:
    """Return compact regression and directional metrics for scheme validation."""

    if len(targets) != len(predictions):
        raise ValueError("target and prediction counts must match")
    if not targets:
        return {
            "row_count": 0,
            "mae": None,
            "rmse": None,
            "mean_prediction": None,
            "mean_target": None,
            "pearson_correlation": None,
            "directional_accuracy_vs_neutral": None,
        }
    pairs = [(float(target), float(prediction)) for target, prediction in zip(targets, predictions)]
    errors = [prediction - target for target, prediction in pairs]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mean_target = sum(target for target, _prediction in pairs) / len(pairs)
    mean_prediction = sum(prediction for _target, prediction in pairs) / len(pairs)
    target_centered = [target - mean_target for target, _prediction in pairs]
    prediction_centered = [prediction - mean_prediction for _target, prediction in pairs]
    target_var = sum(value * value for value in target_centered)
    prediction_var = sum(value * value for value in prediction_centered)
    correlation = (
        sum(a * b for a, b in zip(target_centered, prediction_centered)) / math.sqrt(target_var * prediction_var)
        if target_var > 0 and prediction_var > 0
        else None
    )
    directional = sum((target >= 0.5) == (prediction >= 0.5) for target, prediction in pairs) / len(pairs)
    return {
        "row_count": len(pairs),
        "mae": round(mae, 8),
        "rmse": round(rmse, 8),
        "mean_prediction": round(mean_prediction, 8),
        "mean_target": round(mean_target, 8),
        "pearson_correlation": round(correlation, 8) if correlation is not None else None,
        "directional_accuracy_vs_neutral": round(directional, 8),
    }


def _validate_xy(x: Any, y: Any) -> None:
    if x.ndim != 2 or x.shape[0] == 0 or x.shape[1] == 0:
        raise ValueError("feature_rows must be a non-empty 2D matrix")
    if y.ndim != 1 or len(y) != x.shape[0]:
        raise ValueError("targets must be a 1D vector matching feature_rows")


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _load_numpy() -> Any:
    try:
        import numpy as np  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:  # pragma: no cover
        raise RuntimeError("NumPy is required for continual residual MLP model validation") from error
    return np

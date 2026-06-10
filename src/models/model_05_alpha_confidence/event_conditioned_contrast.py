"""Layer 5 diagnostic contrast for Layer 4 event-conditioned alpha features."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from .training import score_after_cost_alpha, train_after_cost_alpha_model

ARTIFACT_SCHEMA_VERSION = "layer_05_event_conditioned_alpha_contrast"
DIAGNOSTIC_SCOPE = "diagnostic_not_promotion"
DEFAULT_LABEL_FIELD = "after_cost_return_1D"
DEFAULT_TRAIN_FRACTION = 0.70


def build_labeled_focus_pool_rows(
    layer4_rows: Iterable[Mapping[str, Any]],
    layer10_overlay_rows: Iterable[Mapping[str, Any]],
    *,
    horizon: str = "1D",
) -> list[dict[str, Any]]:
    """Join Layer 4 focus-pool rows to Layer 10 replay labels by decision id."""

    label_field = f"after_cost_return_{horizon}"
    overlay_by_decision = {
        str(row.get("decision_id")): row
        for row in layer10_overlay_rows
        if row.get("decision_id") and _safe_float(row.get("excess_return")) is not None
    }
    labeled_rows: list[dict[str, Any]] = []
    for layer4_row in layer4_rows:
        decision_id = decision_id_from_layer4_row(layer4_row)
        overlay = overlay_by_decision.get(decision_id)
        if overlay is None:
            continue
        row = dict(layer4_row)
        row[label_field] = float(overlay["excess_return"])
        row["layer_05_label_source"] = "layer10_replay_excess_return"
        row["layer_05_diagnostic_scope"] = DIAGNOSTIC_SCOPE
        row["source_decision_id"] = decision_id
        row["target_ref"] = overlay.get("target_ref")
        row["visible_event_families"] = list(overlay.get("visible_event_families") or [])
        row["visible_event_count"] = int(overlay.get("visible_event_count") or 0)
        row["layer10_replay_prediction_score"] = overlay.get("prediction_score")
        row["layer10_replay_decision_status"] = overlay.get("decision_status")
        labeled_rows.append(row)
    return sorted(labeled_rows, key=_row_sort_key)


def decision_id_from_layer4_row(row: Mapping[str, Any]) -> str:
    """Extract the Layer 10 replay decision id carried by a Layer 4 focus-pool row."""

    target_candidate_id = str(row.get("target_candidate_id") or "")
    prefix = "layer10_replay_"
    if not target_candidate_id.startswith(prefix):
        raise ValueError(f"Layer 4 focus-pool target_candidate_id lacks {prefix!r}: {target_candidate_id!r}")
    decision_id = target_candidate_id.removeprefix(prefix)
    if not decision_id:
        raise ValueError("Layer 4 focus-pool target_candidate_id has an empty replay decision id")
    return decision_id


def run_event_conditioned_alpha_contrast(
    rows: Sequence[Mapping[str, Any]],
    *,
    horizon: str = "1D",
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    return_scale: float = 0.02,
    iterations: int = 120,
    learning_rate: float = 0.08,
) -> dict[str, Any]:
    """Train baseline vs Layer 4-conditioned Layer 5 artifacts and compare holdout scores."""

    label_field = f"after_cost_return_{horizon}"
    labeled_rows = [dict(row) for row in rows if _safe_float(row.get(label_field)) is not None]
    if len(labeled_rows) < 4:
        raise ValueError("at least four labeled rows are required for a diagnostic train/test contrast")
    labeled_rows.sort(key=_row_sort_key)
    train_rows, test_rows = _time_split(labeled_rows, train_fraction=train_fraction)
    baseline_train_rows = [without_layer4_event_features(row) for row in train_rows]
    baseline_test_rows = [without_layer4_event_features(row) for row in test_rows]

    baseline_artifact = train_after_cost_alpha_model(
        baseline_train_rows,
        horizon=horizon,
        label_field=label_field,
        return_scale=return_scale,
        iterations=iterations,
        learning_rate=learning_rate,
    )
    event_conditioned_artifact = train_after_cost_alpha_model(
        train_rows,
        horizon=horizon,
        label_field=label_field,
        return_scale=return_scale,
        iterations=iterations,
        learning_rate=learning_rate,
    )

    predictions: list[dict[str, Any]] = []
    for original, baseline_row in zip(test_rows, baseline_test_rows):
        realized_return = float(original[label_field])
        target_score = _return_to_score(realized_return, return_scale=return_scale)
        baseline_score = score_after_cost_alpha(baseline_row, baseline_artifact, horizon=horizon)
        event_score = score_after_cost_alpha(original, event_conditioned_artifact, horizon=horizon)
        predictions.append(
            {
                "target_candidate_id": original.get("target_candidate_id"),
                "source_decision_id": original.get("source_decision_id"),
                "available_time": original.get("available_time"),
                "target_ref": original.get("target_ref"),
                "visible_event_families": list(original.get("visible_event_families") or []),
                "realized_after_cost_return": round(realized_return, 8),
                "target_score": round(target_score, 8),
                "baseline_score": baseline_score["score"],
                "event_conditioned_score": event_score["score"],
                "baseline_signed_edge_score": baseline_score["signed_edge_score"],
                "event_conditioned_signed_edge_score": event_score["signed_edge_score"],
            }
        )

    baseline_metrics = _metrics(predictions, prediction_field="baseline_score")
    event_metrics = _metrics(predictions, prediction_field="event_conditioned_score")
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "diagnostic_scope": DIAGNOSTIC_SCOPE,
        "horizon": horizon,
        "label_field": label_field,
        "label_source": "layer10_replay_excess_return",
        "feature_boundary": {
            "baseline": "Layer 5 after-cost artifact with Layer 4 event features removed",
            "event_conditioned": "Layer 5 after-cost artifact consuming frozen Layer 4 event_failure_risk_vector",
            "layer10_parameter_mutation": False,
            "promotion_or_activation": False,
        },
        "row_counts": {
            "labeled": len(labeled_rows),
            "train": len(train_rows),
            "test": len(test_rows),
        },
        "split": {
            "method": "time_ordered_holdout",
            "train_fraction": train_fraction,
            "train_start": train_rows[0].get("available_time"),
            "train_end": train_rows[-1].get("available_time"),
            "test_start": test_rows[0].get("available_time"),
            "test_end": test_rows[-1].get("available_time"),
        },
        "baseline_metrics": baseline_metrics,
        "event_conditioned_metrics": event_metrics,
        "incremental_metrics": {
            "rmse_reduction": round(baseline_metrics["rmse"] - event_metrics["rmse"], 8),
            "mae_reduction": round(baseline_metrics["mae"] - event_metrics["mae"], 8),
            "direction_accuracy_delta": round(
                event_metrics["direction_accuracy"] - baseline_metrics["direction_accuracy"],
                8,
            ),
            "pearson_delta": round(event_metrics["pearson"] - baseline_metrics["pearson"], 8),
        },
        "baseline_training_summary": baseline_artifact.get("training_summary"),
        "event_conditioned_training_summary": event_conditioned_artifact.get("training_summary"),
        "predictions": predictions,
        "baseline_model_artifact": baseline_artifact,
        "event_conditioned_model_artifact": event_conditioned_artifact,
    }


def without_layer4_event_features(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of a Layer 5 row with Layer 4 event features neutralized."""

    output = {str(key): value for key, value in row.items() if not str(key).startswith("4_")}
    output["event_failure_risk_vector"] = {}
    output["event_failure_risk_vector_ref"] = "baseline_without_layer4_event_conditioning"
    return output


def _time_split(rows: Sequence[dict[str, Any]], *, train_fraction: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")
    split_index = max(1, min(len(rows) - 1, int(len(rows) * train_fraction)))
    return list(rows[:split_index]), list(rows[split_index:])


def _metrics(predictions: Sequence[Mapping[str, Any]], *, prediction_field: str) -> dict[str, float]:
    if not predictions:
        raise ValueError("at least one prediction row is required")
    errors = [float(row[prediction_field]) - float(row["target_score"]) for row in predictions]
    absolute_errors = [abs(error) for error in errors]
    squared_errors = [error * error for error in errors]
    direction_hits = [
        (float(row[prediction_field]) >= 0.5) == (float(row["target_score"]) >= 0.5)
        for row in predictions
    ]
    predictions_values = [float(row[prediction_field]) for row in predictions]
    target_values = [float(row["target_score"]) for row in predictions]
    return {
        "sample_count": len(predictions),
        "rmse": round(math.sqrt(sum(squared_errors) / len(squared_errors)), 8),
        "mae": round(sum(absolute_errors) / len(absolute_errors), 8),
        "direction_accuracy": round(sum(1 for hit in direction_hits if hit) / len(direction_hits), 8),
        "mean_prediction_score": round(sum(predictions_values) / len(predictions_values), 8),
        "mean_target_score": round(sum(target_values) / len(target_values), 8),
        "positive_prediction_rate": round(sum(1 for value in predictions_values if value >= 0.5) / len(predictions_values), 8),
        "pearson": round(_pearson(predictions_values, target_values), 8),
    }


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_denominator = math.sqrt(sum((a - left_mean) ** 2 for a in left))
    right_denominator = math.sqrt(sum((b - right_mean) ** 2 for b in right))
    denominator = left_denominator * right_denominator
    return numerator / denominator if denominator else 0.0


def _return_to_score(realized_return: float, *, return_scale: float) -> float:
    scale = max(abs(return_scale), 1e-9)
    return max(0.0, min(1.0, 0.5 + 0.5 * math.tanh(realized_return / scale)))


def _row_sort_key(row: Mapping[str, Any]) -> tuple[datetime, str]:
    return (_parse_time(row.get("available_time")), str(row.get("target_candidate_id") or ""))


def _parse_time(value: Any) -> datetime:
    if value is None:
        return datetime.min
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=None)
    return parsed.replace(tzinfo=None)


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

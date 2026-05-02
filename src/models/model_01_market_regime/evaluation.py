"""Dry-run MarketRegimeModel evaluation artifact builder.

This module intentionally has no database dependency. It builds the rows that
would later be inserted into the generic model-governance tables, but leaves any
real database writes to a separately reviewed runtime path.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DEFAULT_MODEL_ID = "model_01_market_regime"
DEFAULT_FEATURE_SCHEMA = "trading_data"
DEFAULT_FEATURE_TABLE = "feature_01_market_regime"
DEFAULT_MODEL_SCHEMA = "trading_model"
DEFAULT_MODEL_TABLE = "model_01_market_regime"
DEFAULT_SOURCE_KEY = "SOURCE_01_MARKET_REGIME"
DEFAULT_FEATURE_KEY = "FEATURE_01_MARKET_REGIME"
FACTOR_COLUMNS = (
    "price_behavior_factor",
    "trend_certainty_factor",
    "capital_flow_factor",
    "sentiment_factor",
    "valuation_pressure_factor",
    "fundamental_strength_factor",
    "macro_environment_factor",
    "market_structure_factor",
    "risk_stress_factor",
    "transition_pressure",
    "data_quality_score",
)


@dataclass(frozen=True)
class LabelSpec:
    label_name: str
    source_column: str
    horizon: str
    horizon_steps: int
    target_symbol: str = "SPY"


@dataclass(frozen=True)
class EvaluationArtifacts:
    dataset_request: dict[str, Any]
    dataset_snapshot: dict[str, Any]
    dataset_splits: list[dict[str, Any]]
    eval_labels: list[dict[str, Any]]
    eval_run: dict[str, Any]
    eval_metrics: list[dict[str, Any]]

    def as_table_rows(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "model_dataset_request": [self.dataset_request],
            "model_dataset_snapshot": [self.dataset_snapshot],
            "model_dataset_split": self.dataset_splits,
            "model_eval_label": self.eval_labels,
            "model_eval_run": [self.eval_run],
            "model_eval_metric": self.eval_metrics,
        }


DEFAULT_LABEL_SPECS = (
    LabelSpec("future_return", "spy_return_1d", "1_step", 1, "SPY"),
    LabelSpec("future_return", "spy_return_5d", "5_step", 5, "SPY"),
)


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


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _row_time(row: Mapping[str, Any], *, preferred: str) -> datetime:
    return _parse_time(row.get(preferred) or row.get("available_time") or row.get("snapshot_time"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(_canonical_json(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _data_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(_canonical_json(list(rows)).encode("utf-8")).hexdigest()


def _ordered_feature_rows(feature_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in feature_rows]
    rows.sort(key=lambda row: _row_time(row, preferred="snapshot_time"))
    if not rows:
        raise ValueError("at least one feature row is required")
    return rows


def _ordered_model_rows(model_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in model_rows]
    rows.sort(key=lambda row: _row_time(row, preferred="available_time"))
    if not rows:
        raise ValueError("at least one model row is required")
    return rows


def _time_bounds(rows: Sequence[Mapping[str, Any]], *, preferred: str) -> tuple[datetime, datetime]:
    times = [_row_time(row, preferred=preferred) for row in rows]
    return min(times), max(times)


def build_dataset_request(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    model_id: str = DEFAULT_MODEL_ID,
    purpose: str = "evaluation_dry_run",
    required_source_key: str = DEFAULT_SOURCE_KEY,
    required_feature_key: str = DEFAULT_FEATURE_KEY,
) -> dict[str, Any]:
    start, end = _time_bounds(feature_rows, preferred="snapshot_time")
    request_id = _stable_id("mdreq", model_id, purpose, _iso(start), _iso(end), required_source_key, required_feature_key)
    return {
        "request_id": request_id,
        "model_id": model_id,
        "purpose": purpose,
        "required_data_start_time": _iso(start),
        "required_data_end_time": _iso(end),
        "required_source_key": required_source_key,
        "required_feature_key": required_feature_key,
        "request_status": "dry_run_only",
        "request_payload_json": {"write_policy": "no_database_write"},
    }


def build_dataset_snapshot(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
    model_id: str = DEFAULT_MODEL_ID,
    feature_schema: str = DEFAULT_FEATURE_SCHEMA,
    feature_table: str = DEFAULT_FEATURE_TABLE,
    model_config_hash: str | None = None,
) -> dict[str, Any]:
    start, end = _time_bounds(feature_rows, preferred="snapshot_time")
    feature_data_hash = _data_hash(feature_rows)
    snapshot_id = _stable_id("mdsnap", model_id, feature_schema, feature_table, _iso(start), _iso(end), feature_data_hash, model_config_hash)
    return {
        "snapshot_id": snapshot_id,
        "model_id": model_id,
        "request_id": request_id,
        "feature_schema": feature_schema,
        "feature_table": feature_table,
        "data_start_time": _iso(start),
        "data_end_time": _iso(end),
        "feature_row_count": len(feature_rows),
        "feature_data_hash": feature_data_hash,
        "model_config_hash": model_config_hash,
        "snapshot_payload_json": {"write_policy": "no_database_write"},
    }


def build_dataset_splits(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    snapshot_id: str,
) -> list[dict[str, Any]]:
    times = [_row_time(row, preferred="snapshot_time") for row in feature_rows]
    if len(times) < 3:
        return [_split_row(snapshot_id, "train", 0, times[0], times[-1])]

    n = len(times)
    train_end = max(0, int(n * 0.6) - 1)
    validation_start = min(train_end + 1, n - 1)
    validation_end = max(validation_start, int(n * 0.8) - 1)
    test_start = min(validation_end + 1, n - 1)
    splits = [_split_row(snapshot_id, "train", 0, times[0], times[train_end])]
    splits.append(_split_row(snapshot_id, "validation", 1, times[validation_start], times[validation_end]))
    if test_start <= n - 1:
        splits.append(_split_row(snapshot_id, "test", 2, times[test_start], times[-1]))
    return splits


def _split_row(snapshot_id: str, split_name: str, split_order: int, start: datetime, end: datetime) -> dict[str, Any]:
    return {
        "split_id": _stable_id("mdsplit", snapshot_id, split_name, _iso(start), _iso(end)),
        "snapshot_id": snapshot_id,
        "split_name": split_name,
        "split_start_time": _iso(start),
        "split_end_time": _iso(end),
        "split_order": split_order,
        "split_payload_json": {"method": "chronological_60_20_20" if split_order <= 2 else "custom"},
    }


def build_eval_labels(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    snapshot_id: str,
    label_specs: Sequence[LabelSpec] = DEFAULT_LABEL_SPECS,
) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    for index, row in enumerate(feature_rows):
        available_time = _row_time(row, preferred="snapshot_time")
        for spec in label_specs:
            future_index = index + spec.horizon_steps
            if future_index >= len(feature_rows):
                continue
            future_row = feature_rows[future_index]
            label_value = _safe_float(future_row.get(spec.source_column))
            if label_value is None:
                continue
            label_time = _row_time(future_row, preferred="snapshot_time")
            label_id = _stable_id(
                "mdlabel",
                snapshot_id,
                spec.label_name,
                spec.target_symbol,
                spec.horizon,
                _iso(available_time),
            )
            labels.append(
                {
                    "label_id": label_id,
                    "snapshot_id": snapshot_id,
                    "label_name": spec.label_name,
                    "target_symbol": spec.target_symbol,
                    "horizon": spec.horizon,
                    "available_time": _iso(available_time),
                    "label_time": _iso(label_time),
                    "label_value": label_value,
                    "label_payload_json": {
                        "source_column": spec.source_column,
                        "horizon_steps": spec.horizon_steps,
                        "write_policy": "no_database_write",
                    },
                }
            )
    return labels


def build_eval_run(
    *,
    model_id: str,
    snapshot_id: str,
    model_table: str = DEFAULT_MODEL_TABLE,
    model_config_hash: str | None = None,
) -> dict[str, Any]:
    eval_run_id = _stable_id("mdevrun", model_id, snapshot_id, model_table, model_config_hash)
    return {
        "eval_run_id": eval_run_id,
        "model_id": model_id,
        "snapshot_id": snapshot_id,
        "run_name": "market_regime_dry_run_eval",
        "model_version": model_table,
        "config_hash": model_config_hash,
        "run_status": "dry_run_only",
        "run_payload_json": {"write_policy": "no_database_write"},
    }


def build_eval_metrics(
    model_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    splits: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    factor_columns: Sequence[str] = FACTOR_COLUMNS,
) -> list[dict[str, Any]]:
    model_by_time = {_iso(_row_time(row, preferred="available_time")): row for row in model_rows}
    metrics: list[dict[str, Any]] = []
    label_groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for label in labels:
        key = (str(label["label_name"]), str(label["target_symbol"]), str(label["horizon"]))
        label_groups.setdefault(key, []).append(label)

    for split in splits:
        split_start = _parse_time(split["split_start_time"])
        split_end = _parse_time(split["split_end_time"])
        split_labels = [label for label in labels if split_start <= _parse_time(label["available_time"]) <= split_end]
        metrics.append(
            _metric_row(
                eval_run_id,
                split.get("split_id"),
                metric_name="label_count",
                metric_value=float(len(split_labels)),
                payload={"split_name": split.get("split_name")},
            )
        )
        for (label_name, target_symbol, horizon), grouped_labels in label_groups.items():
            labels_in_split = [label for label in grouped_labels if split_start <= _parse_time(label["available_time"]) <= split_end]
            for factor in factor_columns:
                pairs: list[tuple[float, float]] = []
                for label in labels_in_split:
                    model_row = model_by_time.get(str(label["available_time"]))
                    if model_row is None:
                        continue
                    factor_value = _safe_float(model_row.get(factor))
                    label_value = _safe_float(label.get("label_value"))
                    if factor_value is None or label_value is None:
                        continue
                    pairs.append((factor_value, label_value))
                if not pairs:
                    continue
                metrics.append(
                    _metric_row(
                        eval_run_id,
                        split.get("split_id"),
                        label_name=label_name,
                        target_symbol=target_symbol,
                        horizon=horizon,
                        factor_name=factor,
                        metric_name="pair_count",
                        metric_value=float(len(pairs)),
                    )
                )
                metrics.append(
                    _metric_row(
                        eval_run_id,
                        split.get("split_id"),
                        label_name=label_name,
                        target_symbol=target_symbol,
                        horizon=horizon,
                        factor_name=factor,
                        metric_name="coverage",
                        metric_value=len(pairs) / len(labels_in_split) if labels_in_split else 0.0,
                    )
                )
                correlation = _correlation([left for left, _right in pairs], [right for _left, right in pairs])
                if correlation is not None:
                    metrics.append(
                        _metric_row(
                            eval_run_id,
                            split.get("split_id"),
                            label_name=label_name,
                            target_symbol=target_symbol,
                            horizon=horizon,
                            factor_name=factor,
                            metric_name="pearson_correlation",
                            metric_value=correlation,
                        )
                    )
    return metrics


def _metric_row(
    eval_run_id: str,
    split_id: Any,
    *,
    metric_name: str,
    metric_value: float,
    label_name: str | None = None,
    target_symbol: str = "",
    horizon: str | None = None,
    factor_name: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metric_id = _stable_id(
        "mdmetric",
        eval_run_id,
        split_id,
        label_name,
        target_symbol,
        horizon,
        factor_name,
        metric_name,
    )
    return {
        "metric_id": metric_id,
        "eval_run_id": eval_run_id,
        "split_id": split_id,
        "label_name": label_name,
        "target_symbol": target_symbol,
        "horizon": horizon,
        "factor_name": factor_name,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "metric_payload_json": {"write_policy": "no_database_write", **dict(payload or {})},
    }


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_std = pstdev(left)
    right_std = pstdev(right)
    if left_std <= 0 or right_std <= 0:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    covariance = mean((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    return covariance / (left_std * right_std)


def build_evaluation_artifacts(
    *,
    feature_rows: Iterable[Mapping[str, Any]],
    model_rows: Iterable[Mapping[str, Any]],
    model_id: str = DEFAULT_MODEL_ID,
    model_config_hash: str | None = None,
    label_specs: Sequence[LabelSpec] = DEFAULT_LABEL_SPECS,
) -> EvaluationArtifacts:
    ordered_features = _ordered_feature_rows(feature_rows)
    ordered_models = _ordered_model_rows(model_rows)
    request = build_dataset_request(ordered_features, model_id=model_id)
    snapshot = build_dataset_snapshot(
        ordered_features,
        request_id=str(request["request_id"]),
        model_id=model_id,
        model_config_hash=model_config_hash,
    )
    splits = build_dataset_splits(ordered_features, snapshot_id=str(snapshot["snapshot_id"]))
    labels = build_eval_labels(ordered_features, snapshot_id=str(snapshot["snapshot_id"]), label_specs=label_specs)
    eval_run = build_eval_run(
        model_id=model_id,
        snapshot_id=str(snapshot["snapshot_id"]),
        model_config_hash=model_config_hash,
    )
    metrics = build_eval_metrics(ordered_models, labels, splits, eval_run_id=str(eval_run["eval_run_id"]))
    return EvaluationArtifacts(
        dataset_request=request,
        dataset_snapshot=snapshot,
        dataset_splits=splits,
        eval_labels=labels,
        eval_run=eval_run,
        eval_metrics=metrics,
    )


def summarize_artifacts(artifacts: EvaluationArtifacts) -> dict[str, Any]:
    table_rows = artifacts.as_table_rows()
    metric_names = sorted({str(row["metric_name"]) for row in artifacts.eval_metrics})
    return {
        "write_policy": "no_database_write",
        "tables": {table: len(rows) for table, rows in table_rows.items()},
        "metric_names": metric_names,
        "snapshot_id": artifacts.dataset_snapshot["snapshot_id"],
        "eval_run_id": artifacts.eval_run["eval_run_id"],
    }

"""MarketRegimeModel evaluation artifact builder.

The module has no database connection dependency. It builds governance rows and
promotion-evidence summaries from already supplied point-in-time feature/model
rows. Runtime wrappers may feed it fixture rows for development or PostgreSQL
rows for a real read-only promotion evaluation.
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
DEFAULT_DRY_RUN_WRITE_POLICY = "no_database_write"
DEFAULT_DATABASE_READ_WRITE_POLICY = "database_read_only_pending_governance_persistence"
FACTOR_COLUMNS = (
    "1_price_behavior_factor",
    "1_trend_certainty_factor",
    "1_capital_flow_factor",
    "1_sentiment_factor",
    "1_valuation_pressure_factor",
    "1_fundamental_strength_factor",
    "1_macro_environment_factor",
    "1_market_structure_factor",
    "1_risk_stress_factor",
    "1_transition_pressure",
    "1_data_quality_score",
)

DEFAULT_PROMOTION_THRESHOLDS: dict[str, float] = {
    "minimum_feature_rows": 252.0,
    "minimum_model_rows": 252.0,
    "minimum_eval_labels": 200.0,
    "minimum_split_count": 3.0,
    "minimum_pair_count": 30.0,
    "minimum_coverage": 0.80,
    "minimum_factor_abs_pearson": 0.03,
    "minimum_baseline_improvement_abs": 0.00,
    "minimum_stability_sign_consistency": 0.66,
    "maximum_stability_correlation_range": 1.50,
    "maximum_leakage_violation_count": 0.0,
}


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
    request_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
) -> dict[str, Any]:
    start, end = _time_bounds(feature_rows, preferred="snapshot_time")
    request_id = _stable_id("mdreq", model_id, purpose, _iso(start), _iso(end), required_source_key, required_feature_key, evidence_source)
    return {
        "request_id": request_id,
        "model_id": model_id,
        "purpose": purpose,
        "required_data_start_time": _iso(start),
        "required_data_end_time": _iso(end),
        "required_source_key": required_source_key,
        "required_feature_key": required_feature_key,
        "request_status": request_status,
        "request_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source},
    }


def build_dataset_snapshot(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
    model_id: str = DEFAULT_MODEL_ID,
    feature_schema: str = DEFAULT_FEATURE_SCHEMA,
    feature_table: str = DEFAULT_FEATURE_TABLE,
    model_config_hash: str | None = None,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
) -> dict[str, Any]:
    start, end = _time_bounds(feature_rows, preferred="snapshot_time")
    feature_data_hash = _data_hash(feature_rows)
    snapshot_id = _stable_id("mdsnap", model_id, feature_schema, feature_table, _iso(start), _iso(end), feature_data_hash, model_config_hash, evidence_source)
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
        "snapshot_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source},
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
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
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
                        "write_policy": write_policy,
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
    run_name: str = "market_regime_dry_run_eval",
    run_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
    model_row_count: int | None = None,
) -> dict[str, Any]:
    eval_run_id = _stable_id("mdevrun", model_id, snapshot_id, model_table, model_config_hash, run_name, evidence_source)
    payload: dict[str, Any] = {"write_policy": write_policy, "evidence_source": evidence_source}
    if model_row_count is not None:
        payload["model_row_count"] = model_row_count
    return {
        "eval_run_id": eval_run_id,
        "model_id": model_id,
        "snapshot_id": snapshot_id,
        "run_name": run_name,
        "model_version": model_table,
        "config_hash": model_config_hash,
        "run_status": run_status,
        "run_payload_json": payload,
    }


def build_eval_metrics(
    model_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    splits: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    factor_columns: Sequence[str] = FACTOR_COLUMNS,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
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
                payload={"split_name": split.get("split_name"), "metric_family": "metric_value"},
                write_policy=write_policy,
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
                        payload={"metric_family": "metric_value"},
                        write_policy=write_policy,
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
                        payload={"metric_family": "metric_value"},
                        write_policy=write_policy,
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
                            payload={"metric_family": "model_factor"},
                            write_policy=write_policy,
                        )
                    )
    return metrics


def build_baseline_metrics(
    feature_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    splits: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    label_specs: Sequence[LabelSpec] = DEFAULT_LABEL_SPECS,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    feature_by_time = {_iso(_row_time(row, preferred="snapshot_time")): row for row in feature_rows}
    source_by_horizon = {spec.horizon: spec.source_column for spec in label_specs}
    metrics: list[dict[str, Any]] = []
    for split in splits:
        split_start = _parse_time(split["split_start_time"])
        split_end = _parse_time(split["split_end_time"])
        labels_in_split = [label for label in labels if split_start <= _parse_time(label["available_time"]) <= split_end]
        grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for label in labels_in_split:
            grouped.setdefault((str(label["label_name"]), str(label["target_symbol"]), str(label["horizon"])), []).append(label)
        for (label_name, target_symbol, horizon), group in grouped.items():
            source_column = source_by_horizon.get(horizon)
            if not source_column:
                continue
            pairs: list[tuple[float, float]] = []
            for label in group:
                feature_row = feature_by_time.get(str(label["available_time"]))
                if feature_row is None:
                    continue
                baseline_value = _safe_float(feature_row.get(source_column))
                label_value = _safe_float(label.get("label_value"))
                if baseline_value is None or label_value is None:
                    continue
                pairs.append((baseline_value, label_value))
            if len(pairs) < 2:
                continue
            correlation = _correlation([left for left, _right in pairs], [right for _left, right in pairs])
            if correlation is not None:
                metrics.append(
                    _metric_row(
                        eval_run_id,
                        split.get("split_id"),
                        label_name=label_name,
                        target_symbol=target_symbol,
                        horizon=horizon,
                        factor_name=f"baseline_current_{source_column}",
                        metric_name="baseline_pearson_correlation",
                        metric_value=correlation,
                        payload={"metric_family": "baseline", "source_column": source_column},
                        write_policy=write_policy,
                    )
                )
    return metrics


def build_baseline_improvement_metrics(
    metrics: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    factor_max: dict[tuple[Any, str, str, str], float] = {}
    baseline_max: dict[tuple[Any, str, str, str], float] = {}
    for metric in metrics:
        value = _safe_float(metric.get("metric_value"))
        if value is None:
            continue
        key = (metric.get("split_id"), str(metric.get("label_name") or ""), str(metric.get("target_symbol") or ""), str(metric.get("horizon") or ""))
        if metric.get("metric_name") == "pearson_correlation":
            factor_max[key] = max(factor_max.get(key, 0.0), abs(value))
        elif metric.get("metric_name") == "baseline_pearson_correlation":
            baseline_max[key] = max(baseline_max.get(key, 0.0), abs(value))
    output: list[dict[str, Any]] = []
    for key, factor_value in factor_max.items():
        baseline_value = baseline_max.get(key)
        if baseline_value is None:
            continue
        split_id, label_name, target_symbol, horizon = key
        output.append(
            _metric_row(
                eval_run_id,
                split_id,
                label_name=label_name or None,
                target_symbol=target_symbol,
                horizon=horizon or None,
                metric_name="factor_max_abs_pearson_correlation",
                metric_value=factor_value,
                payload={"metric_family": "baseline_comparison"},
                write_policy=write_policy,
            )
        )
        output.append(
            _metric_row(
                eval_run_id,
                split_id,
                label_name=label_name or None,
                target_symbol=target_symbol,
                horizon=horizon or None,
                metric_name="baseline_max_abs_pearson_correlation",
                metric_value=baseline_value,
                payload={"metric_family": "baseline_comparison"},
                write_policy=write_policy,
            )
        )
        output.append(
            _metric_row(
                eval_run_id,
                split_id,
                label_name=label_name or None,
                target_symbol=target_symbol,
                horizon=horizon or None,
                metric_name="baseline_improvement_abs",
                metric_value=factor_value - baseline_value,
                payload={"metric_family": "baseline_comparison"},
                write_policy=write_policy,
            )
        )
    return output


def build_stability_metrics(
    metrics: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[float]] = {}
    for metric in metrics:
        if metric.get("metric_name") != "pearson_correlation":
            continue
        value = _safe_float(metric.get("metric_value"))
        if value is None:
            continue
        key = (
            str(metric.get("label_name") or ""),
            str(metric.get("target_symbol") or ""),
            str(metric.get("horizon") or ""),
            str(metric.get("factor_name") or ""),
        )
        grouped.setdefault(key, []).append(value)
    output: list[dict[str, Any]] = []
    for (label_name, target_symbol, horizon, factor_name), values in grouped.items():
        if len(values) < 2:
            continue
        reference = 1.0 if mean(values) >= 0 else -1.0
        sign_consistency = sum(1 for value in values if value == 0 or (1.0 if value > 0 else -1.0) == reference) / len(values)
        correlation_range = max(values) - min(values)
        output.append(
            _metric_row(
                eval_run_id,
                None,
                label_name=label_name or None,
                target_symbol=target_symbol,
                horizon=horizon or None,
                factor_name=factor_name or None,
                metric_name="split_stability_sign_consistency",
                metric_value=sign_consistency,
                payload={"metric_family": "stability", "split_count": len(values)},
                write_policy=write_policy,
            )
        )
        output.append(
            _metric_row(
                eval_run_id,
                None,
                label_name=label_name or None,
                target_symbol=target_symbol,
                horizon=horizon or None,
                factor_name=factor_name or None,
                metric_name="split_stability_correlation_range",
                metric_value=correlation_range,
                payload={"metric_family": "stability", "split_count": len(values)},
                write_policy=write_policy,
            )
        )
    return output


def build_leakage_metrics(
    model_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    splits: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    model_times = {_iso(_row_time(row, preferred="available_time")) for row in model_rows}
    label_direction_violations = 0
    missing_model_alignment = 0
    for label in labels:
        available_time = _parse_time(label["available_time"])
        label_time = _parse_time(label["label_time"])
        if label_time <= available_time:
            label_direction_violations += 1
        if _iso(available_time) not in model_times:
            missing_model_alignment += 1
    split_overlap_violations = 0
    ordered_splits = sorted(splits, key=lambda split: int(split.get("split_order") or 0))
    for left, right in zip(ordered_splits, ordered_splits[1:], strict=False):
        if _parse_time(left["split_end_time"]) >= _parse_time(right["split_start_time"]):
            split_overlap_violations += 1
    total = float(label_direction_violations + missing_model_alignment + split_overlap_violations)
    return [
        _metric_row(
            eval_run_id,
            None,
            metric_name="no_future_leak_violation_count",
            metric_value=float(label_direction_violations),
            payload={"metric_family": "leakage", "check": "label_time_strictly_after_available_time"},
            write_policy=write_policy,
        ),
        _metric_row(
            eval_run_id,
            None,
            metric_name="model_label_alignment_missing_count",
            metric_value=float(missing_model_alignment),
            payload={"metric_family": "leakage", "check": "model_row_exists_at_label_available_time"},
            write_policy=write_policy,
        ),
        _metric_row(
            eval_run_id,
            None,
            metric_name="chronological_split_overlap_violation_count",
            metric_value=float(split_overlap_violations),
            payload={"metric_family": "leakage", "check": "splits_are_strictly_ordered"},
            write_policy=write_policy,
        ),
        _metric_row(
            eval_run_id,
            None,
            metric_name="total_leakage_violation_count",
            metric_value=total,
            payload={"metric_family": "leakage"},
            write_policy=write_policy,
        ),
    ]


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
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
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
        "metric_payload_json": {"write_policy": write_policy, **dict(payload or {})},
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
    purpose: str = "evaluation_dry_run",
    request_status: str = "dry_run_only",
    run_name: str = "market_regime_dry_run_eval",
    run_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
    feature_schema: str = DEFAULT_FEATURE_SCHEMA,
    feature_table: str = DEFAULT_FEATURE_TABLE,
) -> EvaluationArtifacts:
    ordered_features = _ordered_feature_rows(feature_rows)
    ordered_models = _ordered_model_rows(model_rows)
    request = build_dataset_request(
        ordered_features,
        model_id=model_id,
        purpose=purpose,
        request_status=request_status,
        write_policy=write_policy,
        evidence_source=evidence_source,
    )
    snapshot = build_dataset_snapshot(
        ordered_features,
        request_id=str(request["request_id"]),
        model_id=model_id,
        model_config_hash=model_config_hash,
        write_policy=write_policy,
        evidence_source=evidence_source,
        feature_schema=feature_schema,
        feature_table=feature_table,
    )
    splits = build_dataset_splits(ordered_features, snapshot_id=str(snapshot["snapshot_id"]))
    labels = build_eval_labels(ordered_features, snapshot_id=str(snapshot["snapshot_id"]), label_specs=label_specs, write_policy=write_policy)
    eval_run = build_eval_run(
        model_id=model_id,
        snapshot_id=str(snapshot["snapshot_id"]),
        model_config_hash=model_config_hash,
        run_name=run_name,
        run_status=run_status,
        write_policy=write_policy,
        evidence_source=evidence_source,
        model_row_count=len(ordered_models),
    )
    metrics = build_eval_metrics(ordered_models, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy)
    metrics.extend(build_baseline_metrics(ordered_features, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), label_specs=label_specs, write_policy=write_policy))
    metrics.extend(build_baseline_improvement_metrics(metrics, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_stability_metrics(metrics, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_leakage_metrics(ordered_models, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    return EvaluationArtifacts(
        dataset_request=request,
        dataset_snapshot=snapshot,
        dataset_splits=splits,
        eval_labels=labels,
        eval_run=eval_run,
        eval_metrics=metrics,
    )


def summarize_artifacts(artifacts: EvaluationArtifacts, *, thresholds: Mapping[str, float] | None = None) -> dict[str, Any]:
    table_rows = artifacts.as_table_rows()
    metric_names = sorted({str(row["metric_name"]) for row in artifacts.eval_metrics})
    threshold_values = {**DEFAULT_PROMOTION_THRESHOLDS, **dict(thresholds or {})}
    threshold_results = evaluate_promotion_thresholds(artifacts, threshold_values)
    metric_summary = summarize_metric_values(artifacts.eval_metrics)
    return {
        "write_policy": artifacts.eval_run.get("run_payload_json", {}).get("write_policy", DEFAULT_DRY_RUN_WRITE_POLICY),
        "evidence_source": artifacts.eval_run.get("run_payload_json", {}).get("evidence_source"),
        "request_status": artifacts.dataset_request.get("request_status"),
        "run_status": artifacts.eval_run.get("run_status"),
        "tables": {table: len(rows) for table, rows in table_rows.items()},
        "metric_names": metric_names,
        "metric_value_summary": metric_summary,
        "acceptance_thresholds": threshold_values,
        "threshold_results": threshold_results,
        "baseline_summary": _metric_family_summary(artifacts.eval_metrics, ("baseline_pearson_correlation", "baseline_improvement_abs")),
        "stability_summary": _metric_family_summary(artifacts.eval_metrics, ("split_stability_sign_consistency", "split_stability_correlation_range")),
        "leakage_summary": _metric_family_summary(artifacts.eval_metrics, ("no_future_leak_violation_count", "model_label_alignment_missing_count", "chronological_split_overlap_violation_count", "total_leakage_violation_count")),
        "promotion_evidence_ready": all(result["passed"] for result in threshold_results.values()),
        "snapshot_id": artifacts.dataset_snapshot["snapshot_id"],
        "eval_run_id": artifacts.eval_run["eval_run_id"],
    }


def summarize_metric_values(metrics: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for metric in metrics:
        value = _safe_float(metric.get("metric_value"))
        if value is None:
            continue
        grouped.setdefault(str(metric.get("metric_name")), []).append(value)
    return {name: _numeric_summary(values) for name, values in sorted(grouped.items())}


def _numeric_summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "count": float(len(values)),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
    }


def _metric_family_summary(metrics: Sequence[Mapping[str, Any]], names: Sequence[str]) -> dict[str, dict[str, float]]:
    wanted = set(names)
    return summarize_metric_values([metric for metric in metrics if str(metric.get("metric_name")) in wanted])


def evaluate_promotion_thresholds(artifacts: EvaluationArtifacts, thresholds: Mapping[str, float]) -> dict[str, dict[str, Any]]:
    metric_values = summarize_metric_values(artifacts.eval_metrics)
    checks: dict[str, dict[str, Any]] = {}

    def add(name: str, actual: float, threshold: float, passed: bool, comparator: str) -> None:
        checks[name] = {"actual": actual, "threshold": threshold, "passed": bool(passed), "comparator": comparator}

    feature_rows = float(artifacts.dataset_snapshot.get("feature_row_count") or 0)
    model_rows = float(artifacts.eval_run.get("run_payload_json", {}).get("model_row_count") or 0)
    add("minimum_feature_rows", feature_rows, thresholds["minimum_feature_rows"], feature_rows >= thresholds["minimum_feature_rows"], ">=")
    add("minimum_model_rows", model_rows, thresholds["minimum_model_rows"], model_rows >= thresholds["minimum_model_rows"], ">=")
    add("minimum_eval_labels", float(len(artifacts.eval_labels)), thresholds["minimum_eval_labels"], len(artifacts.eval_labels) >= thresholds["minimum_eval_labels"], ">=")
    add("minimum_split_count", float(len(artifacts.dataset_splits)), thresholds["minimum_split_count"], len(artifacts.dataset_splits) >= thresholds["minimum_split_count"], ">=")

    pair_min = metric_values.get("pair_count", {}).get("min", 0.0)
    coverage_min = metric_values.get("coverage", {}).get("min", 0.0)
    factor_corr_max = max((abs(float(metric.get("metric_value"))) for metric in artifacts.eval_metrics if metric.get("metric_name") == "pearson_correlation" and _safe_float(metric.get("metric_value")) is not None), default=0.0)
    improvement_min = metric_values.get("baseline_improvement_abs", {}).get("min", -1_000_000_000.0)
    stability_sign_min = metric_values.get("split_stability_sign_consistency", {}).get("min", 0.0)
    stability_range_max = metric_values.get("split_stability_correlation_range", {}).get("max", 1_000_000_000.0)
    leakage_max = metric_values.get("total_leakage_violation_count", {}).get("max", 1_000_000_000.0)

    add("minimum_pair_count", pair_min, thresholds["minimum_pair_count"], pair_min >= thresholds["minimum_pair_count"], ">=")
    add("minimum_coverage", coverage_min, thresholds["minimum_coverage"], coverage_min >= thresholds["minimum_coverage"], ">=")
    add("minimum_factor_abs_pearson", factor_corr_max, thresholds["minimum_factor_abs_pearson"], factor_corr_max >= thresholds["minimum_factor_abs_pearson"], ">=")
    add("minimum_baseline_improvement_abs", improvement_min, thresholds["minimum_baseline_improvement_abs"], improvement_min >= thresholds["minimum_baseline_improvement_abs"], ">=")
    add("minimum_stability_sign_consistency", stability_sign_min, thresholds["minimum_stability_sign_consistency"], stability_sign_min >= thresholds["minimum_stability_sign_consistency"], ">=")
    add("maximum_stability_correlation_range", stability_range_max, thresholds["maximum_stability_correlation_range"], stability_range_max <= thresholds["maximum_stability_correlation_range"], "<=")
    add("maximum_leakage_violation_count", leakage_max, thresholds["maximum_leakage_violation_count"], leakage_max <= thresholds["maximum_leakage_violation_count"], "<=")
    return checks

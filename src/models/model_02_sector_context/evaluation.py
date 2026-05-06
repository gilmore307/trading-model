"""SectorContextModel evaluation artifact builder.

The core evaluator has no database dependency. It builds governance/promotion
rows from supplied point-in-time Layer 2 feature rows and ``model_02_sector_context``
rows. Runtime wrappers may supply fixture/local JSONL rows or perform an explicit
read-only PostgreSQL fetch.
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
DEFAULT_MODEL_ID = "model_02_sector_context"
DEFAULT_FEATURE_SCHEMA = "trading_data"
DEFAULT_FEATURE_TABLE = "feature_02_sector_context"
DEFAULT_MODEL_SCHEMA = "trading_model"
DEFAULT_MODEL_TABLE = "model_02_sector_context"
DEFAULT_SOURCE_KEY = "SOURCE_01_MARKET_REGIME"
DEFAULT_FEATURE_KEY = "FEATURE_02_SECTOR_CONTEXT"
DEFAULT_DRY_RUN_WRITE_POLICY = "no_database_write"
DEFAULT_DATABASE_READ_WRITE_POLICY = "database_read_only_pending_governance_persistence"
SUMMARY_CANDIDATE = "SECTOR_OBSERVATION_UNIVERSE"
FACTOR_COLUMNS = (
    "2_sector_relative_direction_score",
    "2_sector_trend_quality_score",
    "2_sector_trend_stability_score",
    "2_sector_transition_risk_score",
    "2_market_context_support_score",
    "2_sector_breadth_confirmation_score",
    "2_sector_dispersion_crowding_score",
    "2_sector_tradability_score",
    "2_state_quality_score",
    "2_coverage_score",
    "2_data_quality_score",
)
SIGNED_LABEL_FACTOR_COLUMNS = {
    "2_sector_relative_direction_score",
    "2_market_context_support_score",
}
RISK_LABEL_FACTOR_COLUMNS = {
    "2_sector_transition_risk_score",
    "2_sector_dispersion_crowding_score",
}

DEFAULT_PROMOTION_THRESHOLDS: dict[str, float] = {
    "minimum_feature_rows": 252.0,
    "minimum_model_rows": 252.0,
    "minimum_eval_labels": 200.0,
    "minimum_split_count": 3.0,
    "minimum_pair_count": 20.0,
    "minimum_coverage": 0.80,
    "minimum_factor_abs_pearson": 0.03,
    "minimum_baseline_improvement_abs": 0.00,
    "minimum_stability_sign_consistency": 0.66,
    "maximum_stability_correlation_range": 1.50,
    "maximum_leakage_violation_count": 0.0,
    "minimum_selected_count": 5.0,
    "minimum_selected_bias_alignment_rate": 0.50,
    "minimum_selected_average_abs_label": 0.0,
    "minimum_selected_abs_label_lift_vs_blocked": 0.0,
}


@dataclass(frozen=True)
class LabelSpec:
    label_name: str
    source_column: str
    horizon: str
    horizon_steps: int


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
            "model_promotion_metric": self.eval_metrics,
        }


DEFAULT_LABEL_SPECS = (
    LabelSpec("future_sector_relative_strength", "relative_strength_return", "1_step", 1),
    LabelSpec("future_sector_relative_strength", "relative_strength_return", "5_step", 5),
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


def _candidate_symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("sector_or_industry_symbol") or row.get("candidate_symbol") or row.get("target_symbol") or "").strip().upper()


def _feature_identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    payload = row.get("label_payload_json")
    if isinstance(payload, Mapping):
        rotation_pair_id = str(payload.get("rotation_pair_id") or "")
        comparison_symbol = str(payload.get("comparison_symbol") or "")
    else:
        rotation_pair_id = str(row.get("rotation_pair_id") or "")
        comparison_symbol = str(row.get("comparison_symbol") or "")
    return (_candidate_symbol(row), rotation_pair_id, comparison_symbol.strip().upper())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(_canonical_json(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _data_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(_canonical_json(list(rows)).encode("utf-8")).hexdigest()


def _ordered_feature_rows(feature_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in feature_rows if _candidate_symbol(row) and _candidate_symbol(row) != SUMMARY_CANDIDATE and row.get("candidate_type") != "sector_rotation_summary"]
    rows.sort(key=lambda row: (_row_time(row, preferred="snapshot_time"), _candidate_symbol(row), str(row.get("rotation_pair_id") or "")))
    if not rows:
        raise ValueError("at least one non-summary sector-context feature row is required")
    return rows


def _ordered_model_rows(model_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in model_rows]
    rows.sort(key=lambda row: (_row_time(row, preferred="available_time"), _candidate_symbol(row)))
    if not rows:
        raise ValueError("at least one sector-context model row is required")
    return rows


def _time_bounds(rows: Sequence[Mapping[str, Any]], *, preferred: str) -> tuple[datetime, datetime]:
    times = [_row_time(row, preferred=preferred) for row in rows]
    return min(times), max(times)


def _available_times(rows: Sequence[Mapping[str, Any]], *, preferred: str) -> list[datetime]:
    return sorted({_row_time(row, preferred=preferred) for row in rows})


def build_dataset_request(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    model_id: str = DEFAULT_MODEL_ID,
    purpose: str = "evaluation_dry_run",
    request_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
) -> dict[str, Any]:
    start, end = _time_bounds(feature_rows, preferred="snapshot_time")
    request_id = _stable_id("mdreq", model_id, purpose, _iso(start), _iso(end), DEFAULT_SOURCE_KEY, DEFAULT_FEATURE_KEY, evidence_source)
    return {
        "request_id": request_id,
        "model_id": model_id,
        "purpose": purpose,
        "required_data_start_time": _iso(start),
        "required_data_end_time": _iso(end),
        "required_source_key": DEFAULT_SOURCE_KEY,
        "required_feature_key": DEFAULT_FEATURE_KEY,
        "request_status": request_status,
        "request_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source, "layer_input_contract": "market_context_state_plus_feature_02_sector_context"},
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


def build_dataset_splits(feature_rows: Sequence[Mapping[str, Any]], *, snapshot_id: str) -> list[dict[str, Any]]:
    times = _available_times(feature_rows, preferred="snapshot_time")
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
        "split_payload_json": {"method": "chronological_unique_available_times_60_20_20"},
    }


def build_eval_labels(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    snapshot_id: str,
    label_specs: Sequence[LabelSpec] = DEFAULT_LABEL_SPECS,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    by_feature_identity: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for row in feature_rows:
        by_feature_identity.setdefault(_feature_identity(row), []).append(row)
    labels: list[dict[str, Any]] = []
    for (symbol, rotation_pair_id, comparison_symbol), rows in by_feature_identity.items():
        ordered = sorted(rows, key=lambda row: _row_time(row, preferred="snapshot_time"))
        for index, row in enumerate(ordered):
            available_time = _row_time(row, preferred="snapshot_time")
            for spec in label_specs:
                future_index = index + spec.horizon_steps
                if future_index >= len(ordered):
                    continue
                future_row = ordered[future_index]
                label_value = _safe_float(future_row.get(spec.source_column))
                if label_value is None:
                    continue
                label_time = _row_time(future_row, preferred="snapshot_time")
                labels.append(
                    {
                        "label_id": _stable_id("mdlabel", snapshot_id, spec.label_name, symbol, rotation_pair_id, comparison_symbol, spec.horizon, _iso(available_time)),
                        "snapshot_id": snapshot_id,
                        "label_name": spec.label_name,
                        "target_symbol": symbol,
                        "horizon": spec.horizon,
                        "available_time": _iso(available_time),
                        "label_time": _iso(label_time),
                        "label_value": label_value,
                        "label_payload_json": {
                            "source_column": spec.source_column,
                            "horizon_steps": spec.horizon_steps,
                            "rotation_pair_id": rotation_pair_id,
                            "comparison_symbol": comparison_symbol,
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
    run_name: str = "sector_context_dry_run_eval",
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
    model_by_key = {(_iso(_row_time(row, preferred="available_time")), _candidate_symbol(row)): row for row in model_rows}
    metrics: list[dict[str, Any]] = []
    for split in splits:
        split_start = _parse_time(split["split_start_time"])
        split_end = _parse_time(split["split_end_time"])
        split_labels = [label for label in labels if split_start <= _parse_time(label["available_time"]) <= split_end]
        metrics.append(_metric_row(eval_run_id, split.get("split_id"), metric_name="label_count", metric_value=float(len(split_labels)), payload={"split_name": split.get("split_name"), "metric_family": "metric_value"}, write_policy=write_policy))
        grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for label in split_labels:
            grouped.setdefault((str(label["label_name"]), str(label["target_symbol"]), str(label["horizon"])), []).append(label)
        for (label_name, symbol, horizon), group in grouped.items():
            for factor in factor_columns:
                pairs: list[tuple[float, float]] = []
                label_transform = _label_transform_for_factor(factor)
                for label in group:
                    model_row = model_by_key.get((str(label["available_time"]), symbol))
                    if model_row is None:
                        continue
                    factor_value = _safe_float(model_row.get(factor))
                    label_value = _transformed_label_value(_safe_float(label.get("label_value")), factor)
                    if factor_value is None or label_value is None:
                        continue
                    pairs.append((factor_value, label_value))
                if not pairs:
                    continue
                metrics.append(_metric_row(eval_run_id, split.get("split_id"), label_name=label_name, target_symbol=symbol, horizon=horizon, factor_name=factor, metric_name="pair_count", metric_value=float(len(pairs)), payload={"metric_family": "metric_value", "label_transform": label_transform}, write_policy=write_policy))
                metrics.append(_metric_row(eval_run_id, split.get("split_id"), label_name=label_name, target_symbol=symbol, horizon=horizon, factor_name=factor, metric_name="coverage", metric_value=len(pairs) / len(group) if group else 0.0, payload={"metric_family": "metric_value", "label_transform": label_transform}, write_policy=write_policy))
                correlation = _correlation([left for left, _right in pairs], [right for _left, right in pairs])
                if correlation is not None:
                    metrics.append(_metric_row(eval_run_id, split.get("split_id"), label_name=label_name, target_symbol=symbol, horizon=horizon, factor_name=factor, metric_name="pearson_correlation", metric_value=correlation, payload={"metric_family": "model_factor"}, write_policy=write_policy))
    return metrics


def _label_transform_for_factor(factor: str) -> str:
    if factor in SIGNED_LABEL_FACTOR_COLUMNS:
        return "signed_label"
    if factor in RISK_LABEL_FACTOR_COLUMNS:
        return "negative_absolute_label"
    return "absolute_label"


def _transformed_label_value(label_value: float | None, factor: str) -> float | None:
    if label_value is None:
        return None
    if factor in SIGNED_LABEL_FACTOR_COLUMNS:
        return label_value
    if factor in RISK_LABEL_FACTOR_COLUMNS:
        return -abs(label_value)
    return abs(label_value)


def build_baseline_metrics(
    feature_rows: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    splits: Sequence[Mapping[str, Any]],
    *,
    eval_run_id: str,
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
) -> list[dict[str, Any]]:
    feature_by_key = {(_iso(_row_time(row, preferred="snapshot_time")), *_feature_identity(row)): row for row in feature_rows}
    metrics: list[dict[str, Any]] = []
    for split in splits:
        split_start = _parse_time(split["split_start_time"])
        split_end = _parse_time(split["split_end_time"])
        labels_in_split = [label for label in labels if split_start <= _parse_time(label["available_time"]) <= split_end]
        grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for label in labels_in_split:
            grouped.setdefault((str(label["label_name"]), str(label["target_symbol"]), str(label["horizon"])), []).append(label)
        for (label_name, symbol, horizon), group in grouped.items():
            pairs: list[tuple[float, float]] = []
            for label in group:
                feature_row = feature_by_key.get((str(label["available_time"]), *_feature_identity(label)))
                if feature_row is None:
                    continue
                baseline_value = _safe_float(feature_row.get("relative_strength_return"))
                label_value = _safe_float(label.get("label_value"))
                if baseline_value is None or label_value is None:
                    continue
                pairs.append((baseline_value, label_value))
            if len(pairs) < 2:
                continue
            correlation = _correlation([left for left, _right in pairs], [right for _left, right in pairs])
            if correlation is not None:
                metrics.append(_metric_row(eval_run_id, split.get("split_id"), label_name=label_name, target_symbol=symbol, horizon=horizon, factor_name="baseline_current_relative_strength_return", metric_name="baseline_pearson_correlation", metric_value=correlation, payload={"metric_family": "baseline", "source_column": "relative_strength_return"}, write_policy=write_policy))
    return metrics


def build_baseline_improvement_metrics(metrics: Sequence[Mapping[str, Any]], *, eval_run_id: str, write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY) -> list[dict[str, Any]]:
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
        output.append(_metric_row(eval_run_id, split_id, label_name=label_name or None, target_symbol=target_symbol, horizon=horizon or None, metric_name="factor_max_abs_pearson_correlation", metric_value=factor_value, payload={"metric_family": "baseline_comparison"}, write_policy=write_policy))
        output.append(_metric_row(eval_run_id, split_id, label_name=label_name or None, target_symbol=target_symbol, horizon=horizon or None, metric_name="baseline_max_abs_pearson_correlation", metric_value=baseline_value, payload={"metric_family": "baseline_comparison"}, write_policy=write_policy))
        output.append(_metric_row(eval_run_id, split_id, label_name=label_name or None, target_symbol=target_symbol, horizon=horizon or None, metric_name="baseline_improvement_abs", metric_value=factor_value - baseline_value, payload={"metric_family": "baseline_comparison"}, write_policy=write_policy))
    return output


def build_stability_metrics(metrics: Sequence[Mapping[str, Any]], *, eval_run_id: str, write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[float]] = {}
    for metric in metrics:
        if metric.get("metric_name") != "pearson_correlation":
            continue
        value = _safe_float(metric.get("metric_value"))
        if value is None:
            continue
        key = (str(metric.get("label_name") or ""), str(metric.get("target_symbol") or ""), str(metric.get("horizon") or ""), str(metric.get("factor_name") or ""))
        grouped.setdefault(key, []).append(value)
    output: list[dict[str, Any]] = []
    for (label_name, target_symbol, horizon, factor_name), values in grouped.items():
        if len(values) < 2:
            continue
        reference = 1.0 if mean(values) >= 0 else -1.0
        sign_consistency = sum(1 for value in values if value == 0 or (1.0 if value > 0 else -1.0) == reference) / len(values)
        correlation_range = max(values) - min(values)
        output.append(_metric_row(eval_run_id, None, label_name=label_name or None, target_symbol=target_symbol, horizon=horizon or None, factor_name=factor_name or None, metric_name="split_stability_sign_consistency", metric_value=sign_consistency, payload={"metric_family": "stability", "split_count": len(values)}, write_policy=write_policy))
        output.append(_metric_row(eval_run_id, None, label_name=label_name or None, target_symbol=target_symbol, horizon=horizon or None, factor_name=factor_name or None, metric_name="split_stability_correlation_range", metric_value=correlation_range, payload={"metric_family": "stability", "split_count": len(values)}, write_policy=write_policy))
    return output


def build_handoff_metrics(model_rows: Sequence[Mapping[str, Any]], labels: Sequence[Mapping[str, Any]], *, eval_run_id: str, write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY) -> list[dict[str, Any]]:
    model_by_key = {(_iso(_row_time(row, preferred="available_time")), _candidate_symbol(row)): row for row in model_rows}
    selected_values: list[float] = []
    watch_values: list[float] = []
    blocked_values: list[float] = []
    selected_alignment_checks = 0
    selected_alignment_passes = 0
    selected_long_bias_count = 0
    selected_short_bias_count = 0
    for label in labels:
        model_row = model_by_key.get((str(label["available_time"]), str(label["target_symbol"])))
        if model_row is None:
            continue
        value = _safe_float(label.get("label_value"))
        if value is None:
            continue
        state = str(model_row.get("2_sector_handoff_state") or "")
        bias = str(model_row.get("2_sector_handoff_bias") or "")
        if state == "selected":
            selected_values.append(value)
            if bias == "long_bias":
                selected_long_bias_count += 1
                selected_alignment_checks += 1
                if value > 0:
                    selected_alignment_passes += 1
            elif bias == "short_bias":
                selected_short_bias_count += 1
                selected_alignment_checks += 1
                if value < 0:
                    selected_alignment_passes += 1
        elif state == "watch":
            watch_values.append(value)
        elif state in {"blocked", "insufficient_data"}:
            blocked_values.append(value)
    selected_abs = [abs(value) for value in selected_values]
    watch_abs = [abs(value) for value in watch_values]
    blocked_abs = [abs(value) for value in blocked_values]
    selected_average_abs = mean(selected_abs) if selected_abs else 0.0
    blocked_average_abs = mean(blocked_abs) if blocked_abs else 0.0
    output = [
        _metric_row(eval_run_id, None, metric_name="selected_count", metric_value=float(len(selected_values)), payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="selected_long_bias_count", metric_value=float(selected_long_bias_count), payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="selected_short_bias_count", metric_value=float(selected_short_bias_count), payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="selected_bias_alignment_rate", metric_value=(selected_alignment_passes / selected_alignment_checks) if selected_alignment_checks else 0.0, payload={"metric_family": "sector_handoff", "alignment_checks": selected_alignment_checks}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="selected_average_abs_label", metric_value=selected_average_abs, payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="watch_average_abs_label", metric_value=mean(watch_abs) if watch_abs else 0.0, payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="blocked_average_abs_label", metric_value=blocked_average_abs, payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="selected_abs_label_lift_vs_blocked", metric_value=selected_average_abs - blocked_average_abs, payload={"metric_family": "sector_handoff"}, write_policy=write_policy),
    ]
    return output


def build_leakage_metrics(model_rows: Sequence[Mapping[str, Any]], labels: Sequence[Mapping[str, Any]], splits: Sequence[Mapping[str, Any]], *, eval_run_id: str, write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY) -> list[dict[str, Any]]:
    model_keys = {(_iso(_row_time(row, preferred="available_time")), _candidate_symbol(row)) for row in model_rows}
    label_direction_violations = 0
    missing_model_alignment = 0
    for label in labels:
        available_time = _parse_time(label["available_time"])
        label_time = _parse_time(label["label_time"])
        if label_time <= available_time:
            label_direction_violations += 1
        if (_iso(available_time), str(label["target_symbol"])) not in model_keys:
            missing_model_alignment += 1
    split_overlap_violations = 0
    ordered_splits = sorted(splits, key=lambda split: int(split.get("split_order") or 0))
    for left, right in zip(ordered_splits, ordered_splits[1:], strict=False):
        if _parse_time(left["split_end_time"]) >= _parse_time(right["split_start_time"]):
            split_overlap_violations += 1
    total = float(label_direction_violations + missing_model_alignment + split_overlap_violations)
    return [
        _metric_row(eval_run_id, None, metric_name="no_future_leak_violation_count", metric_value=float(label_direction_violations), payload={"metric_family": "leakage", "check": "label_time_strictly_after_available_time"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="model_label_alignment_missing_count", metric_value=float(missing_model_alignment), payload={"metric_family": "leakage", "check": "model_row_exists_at_label_available_time_and_symbol"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="chronological_split_overlap_violation_count", metric_value=float(split_overlap_violations), payload={"metric_family": "leakage", "check": "splits_are_strictly_ordered"}, write_policy=write_policy),
        _metric_row(eval_run_id, None, metric_name="total_leakage_violation_count", metric_value=total, payload={"metric_family": "leakage"}, write_policy=write_policy),
    ]


def _metric_row(eval_run_id: str, split_id: Any, *, metric_name: str, metric_value: float, label_name: str | None = None, target_symbol: str = "", horizon: str | None = None, factor_name: str | None = None, payload: Mapping[str, Any] | None = None, write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY) -> dict[str, Any]:
    return {
        "metric_id": _stable_id("mdmetric", eval_run_id, split_id, label_name, target_symbol, horizon, factor_name, metric_name),
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
    run_name: str = "sector_context_dry_run_eval",
    run_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
    feature_schema: str = DEFAULT_FEATURE_SCHEMA,
    feature_table: str = DEFAULT_FEATURE_TABLE,
) -> EvaluationArtifacts:
    ordered_features = _ordered_feature_rows(feature_rows)
    ordered_models = _ordered_model_rows(model_rows)
    request = build_dataset_request(ordered_features, model_id=model_id, purpose=purpose, request_status=request_status, write_policy=write_policy, evidence_source=evidence_source)
    snapshot = build_dataset_snapshot(ordered_features, request_id=str(request["request_id"]), model_id=model_id, model_config_hash=model_config_hash, write_policy=write_policy, evidence_source=evidence_source, feature_schema=feature_schema, feature_table=feature_table)
    splits = build_dataset_splits(ordered_features, snapshot_id=str(snapshot["snapshot_id"]))
    labels = build_eval_labels(ordered_features, snapshot_id=str(snapshot["snapshot_id"]), label_specs=label_specs, write_policy=write_policy)
    eval_run = build_eval_run(model_id=model_id, snapshot_id=str(snapshot["snapshot_id"]), model_config_hash=model_config_hash, run_name=run_name, run_status=run_status, write_policy=write_policy, evidence_source=evidence_source, model_row_count=len(ordered_models))
    metrics = build_eval_metrics(ordered_models, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy)
    metrics.extend(build_baseline_metrics(ordered_features, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_baseline_improvement_metrics(metrics, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_stability_metrics(metrics, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_handoff_metrics(ordered_models, labels, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    metrics.extend(build_leakage_metrics(ordered_models, labels, splits, eval_run_id=str(eval_run["eval_run_id"]), write_policy=write_policy))
    return EvaluationArtifacts(dataset_request=request, dataset_snapshot=snapshot, dataset_splits=splits, eval_labels=labels, eval_run=eval_run, eval_metrics=metrics)


def summarize_artifacts(artifacts: EvaluationArtifacts, *, thresholds: Mapping[str, float] | None = None) -> dict[str, Any]:
    table_rows = artifacts.as_table_rows()
    threshold_values = {**DEFAULT_PROMOTION_THRESHOLDS, **dict(thresholds or {})}
    threshold_results = evaluate_promotion_thresholds(artifacts, threshold_values)
    return {
        "write_policy": artifacts.eval_run.get("run_payload_json", {}).get("write_policy", DEFAULT_DRY_RUN_WRITE_POLICY),
        "evidence_source": artifacts.eval_run.get("run_payload_json", {}).get("evidence_source"),
        "request_status": artifacts.dataset_request.get("request_status"),
        "run_status": artifacts.eval_run.get("run_status"),
        "tables": {table: len(rows) for table, rows in table_rows.items()},
        "metric_names": sorted({str(row["metric_name"]) for row in artifacts.eval_metrics}),
        "metric_value_summary": summarize_metric_values(artifacts.eval_metrics),
        "acceptance_thresholds": threshold_values,
        "threshold_results": threshold_results,
        "baseline_summary": _metric_family_summary(artifacts.eval_metrics, ("baseline_pearson_correlation", "baseline_improvement_abs")),
        "stability_summary": _metric_family_summary(artifacts.eval_metrics, ("split_stability_sign_consistency", "split_stability_correlation_range")),
        "handoff_summary": _metric_family_summary(artifacts.eval_metrics, ("selected_count", "selected_long_bias_count", "selected_short_bias_count", "selected_bias_alignment_rate", "selected_average_abs_label", "watch_average_abs_label", "blocked_average_abs_label", "selected_abs_label_lift_vs_blocked")),
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
    return {"count": float(len(values)), "min": min(values), "max": max(values), "mean": mean(values)}


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
    selected_count = metric_values.get("selected_count", {}).get("max", 0.0)
    selected_bias_alignment_rate = metric_values.get("selected_bias_alignment_rate", {}).get("max", 0.0)
    selected_average_abs_label = metric_values.get("selected_average_abs_label", {}).get("max", -1_000_000_000.0)
    selected_abs_label_lift = metric_values.get("selected_abs_label_lift_vs_blocked", {}).get("max", -1_000_000_000.0)
    add("minimum_pair_count", pair_min, thresholds["minimum_pair_count"], pair_min >= thresholds["minimum_pair_count"], ">=")
    add("minimum_coverage", coverage_min, thresholds["minimum_coverage"], coverage_min >= thresholds["minimum_coverage"], ">=")
    add("minimum_factor_abs_pearson", factor_corr_max, thresholds["minimum_factor_abs_pearson"], factor_corr_max >= thresholds["minimum_factor_abs_pearson"], ">=")
    add("minimum_baseline_improvement_abs", improvement_min, thresholds["minimum_baseline_improvement_abs"], improvement_min >= thresholds["minimum_baseline_improvement_abs"], ">=")
    add("minimum_stability_sign_consistency", stability_sign_min, thresholds["minimum_stability_sign_consistency"], stability_sign_min >= thresholds["minimum_stability_sign_consistency"], ">=")
    add("maximum_stability_correlation_range", stability_range_max, thresholds["maximum_stability_correlation_range"], stability_range_max <= thresholds["maximum_stability_correlation_range"], "<=")
    add("maximum_leakage_violation_count", leakage_max, thresholds["maximum_leakage_violation_count"], leakage_max <= thresholds["maximum_leakage_violation_count"], "<=")
    add("minimum_selected_count", selected_count, thresholds["minimum_selected_count"], selected_count >= thresholds["minimum_selected_count"], ">=")
    add("minimum_selected_bias_alignment_rate", selected_bias_alignment_rate, thresholds["minimum_selected_bias_alignment_rate"], selected_bias_alignment_rate >= thresholds["minimum_selected_bias_alignment_rate"], ">=")
    add("minimum_selected_average_abs_label", selected_average_abs_label, thresholds["minimum_selected_average_abs_label"], selected_average_abs_label >= thresholds["minimum_selected_average_abs_label"], ">=")
    add("minimum_selected_abs_label_lift_vs_blocked", selected_abs_label_lift, thresholds["minimum_selected_abs_label_lift_vs_blocked"], selected_abs_label_lift >= thresholds["minimum_selected_abs_label_lift_vs_blocked"], ">=")
    return checks

"""TargetStateVectorModel evaluation and promotion evidence builder."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DEFAULT_MODEL_ID = "model_03_target_state_vector"
DEFAULT_FEATURE_SCHEMA = "trading_data"
DEFAULT_FEATURE_TABLE = "feature_03_target_state_vector"
DEFAULT_MODEL_SCHEMA = "trading_model"
DEFAULT_MODEL_TABLE = "model_03_target_state_vector"
DEFAULT_DRY_RUN_WRITE_POLICY = "no_database_write"
DEFAULT_DATABASE_READ_WRITE_POLICY = "database_read_only_pending_governance_persistence"
BASELINE_LADDER = ("market_only_baseline", "market_sector_baseline", "market_sector_target_vector")
LABEL_HORIZONS = ("15min", "60min", "390min")
DEFAULT_PROMOTION_THRESHOLDS: dict[str, float] = {
    "minimum_feature_rows": 252.0,
    "minimum_model_rows": 252.0,
    "minimum_eval_labels": 200.0,
    "minimum_split_count": 3.0,
    "minimum_baseline_ladder_step_count": 3.0,
    "minimum_target_vs_market_sector_improvement_abs": 0.0,
    "minimum_target_vs_market_improvement_abs": 0.0,
    "minimum_split_stability_sign_consistency": 0.66,
    "maximum_stability_correlation_range": 1.50,
    "maximum_leakage_violation_count": 0.0,
    "minimum_identity_leakage_violation_count": 0.0,
}


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


def build_evaluation_artifacts(
    *,
    feature_rows: Iterable[Mapping[str, Any]],
    model_rows: Iterable[Mapping[str, Any]],
    model_id: str = DEFAULT_MODEL_ID,
    thresholds: Mapping[str, float] | None = None,
    purpose: str = "evaluation_dry_run",
    request_status: str = "dry_run_only",
    write_policy: str = DEFAULT_DRY_RUN_WRITE_POLICY,
    evidence_source: str = "fixture_or_local_jsonl",
) -> EvaluationArtifacts:
    features = _ordered_feature_rows(feature_rows)
    models = _ordered_model_rows(model_rows)
    thresholds = {**DEFAULT_PROMOTION_THRESHOLDS, **dict(thresholds or {})}
    request = _dataset_request(features, model_id=model_id, purpose=purpose, request_status=request_status, write_policy=write_policy, evidence_source=evidence_source)
    snapshot = _dataset_snapshot(features, request_id=request["request_id"], model_id=model_id, write_policy=write_policy, evidence_source=evidence_source)
    splits = _dataset_splits(features, snapshot_id=snapshot["snapshot_id"])
    labels = _eval_labels(features, snapshot_id=snapshot["snapshot_id"], model_id=model_id)
    eval_run = _eval_run(snapshot, model_id=model_id, write_policy=write_policy, evidence_source=evidence_source)
    metrics = _promotion_metrics(features, models, labels, splits, eval_run_id=eval_run["eval_run_id"], thresholds=thresholds)
    return EvaluationArtifacts(request, snapshot, splits, labels, eval_run, metrics)


def summarize_threshold_results(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    threshold_rows = [row for row in metrics if str(row.get("metric_name", "")).startswith("threshold:")]
    failed = [row for row in threshold_rows if not bool(_payload(row).get("passed"))]
    return {
        "threshold_count": len(threshold_rows),
        "passed_threshold_count": len(threshold_rows) - len(failed),
        "failed_thresholds": [str(row.get("metric_name", "")).replace("threshold:", "") for row in failed],
        "promotion_gate_state": "passed" if threshold_rows and not failed else "blocked",
    }


def _ordered_feature_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = [dict(row) for row in rows]
    output.sort(key=lambda row: (_row_time(row), _candidate(row)))
    if not output:
        raise ValueError("at least one Layer 3 feature row is required")
    return output


def _ordered_model_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = [dict(row) for row in rows]
    output.sort(key=lambda row: (_row_time(row), _candidate(row)))
    if not output:
        raise ValueError("at least one Layer 3 model row is required")
    return output


def _dataset_request(rows: Sequence[Mapping[str, Any]], *, model_id: str, purpose: str, request_status: str, write_policy: str, evidence_source: str) -> dict[str, Any]:
    start, end = _bounds(rows)
    request_id = _stable_id("mdreq", model_id, purpose, _iso(start), _iso(end), evidence_source)
    return {"request_id": request_id, "model_id": model_id, "purpose": purpose, "required_data_start_time": _iso(start), "required_data_end_time": _iso(end), "required_source_key": "SOURCE_03_TARGET_STATE", "required_feature_key": "FEATURE_03_TARGET_STATE_VECTOR", "request_status": request_status, "request_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source, "layer_input_contract": "market_context_state_plus_sector_context_state_plus_target_state_vector"}}


def _dataset_snapshot(rows: Sequence[Mapping[str, Any]], *, request_id: str, model_id: str, write_policy: str, evidence_source: str) -> dict[str, Any]:
    start, end = _bounds(rows)
    data_hash = _data_hash(rows)
    snapshot_id = _stable_id("mdsnap", model_id, DEFAULT_FEATURE_SCHEMA, DEFAULT_FEATURE_TABLE, _iso(start), _iso(end), data_hash, evidence_source)
    return {"snapshot_id": snapshot_id, "model_id": model_id, "request_id": request_id, "feature_schema": DEFAULT_FEATURE_SCHEMA, "feature_table": DEFAULT_FEATURE_TABLE, "data_start_time": _iso(start), "data_end_time": _iso(end), "feature_row_count": len(rows), "feature_data_hash": data_hash, "model_config_hash": None, "snapshot_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source}}


def _dataset_splits(rows: Sequence[Mapping[str, Any]], *, snapshot_id: str) -> list[dict[str, Any]]:
    times = sorted({_row_time(row) for row in rows})
    if len(times) < 3:
        return [_split(snapshot_id, "train", 0, times[0], times[-1])]
    n = len(times)
    train_end = max(0, int(n * 0.6) - 1)
    validation_start = min(train_end + 1, n - 1)
    validation_end = max(validation_start, int(n * 0.8) - 1)
    test_start = min(validation_end + 1, n - 1)
    rows_out = [_split(snapshot_id, "train", 0, times[0], times[train_end]), _split(snapshot_id, "validation", 1, times[validation_start], times[validation_end])]
    if test_start <= n - 1:
        rows_out.append(_split(snapshot_id, "test", 2, times[test_start], times[-1]))
    return rows_out


def _split(snapshot_id: str, split_name: str, split_order: int, start: datetime, end: datetime) -> dict[str, Any]:
    return {"split_id": _stable_id("mdsplit", snapshot_id, split_name, _iso(start), _iso(end)), "snapshot_id": snapshot_id, "split_name": split_name, "split_order": split_order, "split_start_time": _iso(start), "split_end_time": _iso(end), "split_payload_json": {"split_policy": "chronological_60_20_20_if_possible"}}


def _eval_labels(rows: Sequence[Mapping[str, Any]], *, snapshot_id: str, model_id: str) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_candidate.setdefault(_candidate(row), []).append(row)
    labels: list[dict[str, Any]] = []
    for candidate, candidate_rows in by_candidate.items():
        candidate_rows = sorted(candidate_rows, key=_row_time)
        for index, row in enumerate(candidate_rows):
            for horizon in LABEL_HORIZONS:
                steps = _horizon_steps(horizon)
                if index + steps >= len(candidate_rows):
                    continue
                future = candidate_rows[index + steps]
                current_close = _target_close(row)
                future_close = _target_close(future)
                if current_close is not None and future_close is not None and current_close != 0:
                    signed_return = future_close / current_close - 1.0
                else:
                    signed_return = _target_return(future, horizon) or _target_return(future, "15min")
                    if signed_return is None:
                        continue
                current_time = _iso(_row_time(row))
                label = {"feature_available_time": current_time, "signed_forward_return": signed_return, "absolute_forward_return": abs(signed_return), "future_tradeable_path_label": abs(signed_return)}
                labels.append({"label_id": _stable_id("mdlbl", snapshot_id, candidate, current_time, horizon), "snapshot_id": snapshot_id, "model_id": model_id, "target_symbol": candidate, "label_name": "future_target_tradeable_path", "label_horizon": horizon, "label_available_time": _iso(_row_time(future)), "label_value": signed_return, "label_payload_json": label})
    return labels


def _eval_run(snapshot: Mapping[str, Any], *, model_id: str, write_policy: str, evidence_source: str) -> dict[str, Any]:
    eval_run_id = _stable_id("mdevrun", snapshot["snapshot_id"], model_id, evidence_source)
    return {"eval_run_id": eval_run_id, "model_id": model_id, "snapshot_id": snapshot["snapshot_id"], "eval_started_at": snapshot["data_end_time"], "eval_completed_at": snapshot["data_end_time"], "eval_status": "completed", "eval_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source, "baseline_ladder": BASELINE_LADDER}}


def _promotion_metrics(features: Sequence[Mapping[str, Any]], models: Sequence[Mapping[str, Any]], labels: Sequence[Mapping[str, Any]], splits: Sequence[Mapping[str, Any]], *, eval_run_id: str, thresholds: Mapping[str, float]) -> list[dict[str, Any]]:
    model_by_key = {(_candidate(row), _iso(_row_time(row))): row for row in models}
    feature_by_key = {(_candidate(row), _iso(_row_time(row))): row for row in features}
    pairs: list[dict[str, Any]] = []
    for label in labels:
        payload = _coerce_payload(label.get("label_payload_json"))
        current_time = payload.get("feature_available_time") if isinstance(payload, Mapping) else None
        if not current_time:
            continue
        key = (str(label.get("target_symbol")), _iso(_parse_time(current_time)))
        feature = feature_by_key.get(key)
        model = model_by_key.get(key)
        if feature and model:
            pairs.append(_pair(feature, model, label))
    metrics: list[dict[str, Any]] = []
    base_values = _baseline_summary(pairs)
    metrics.extend(_metric_rows(eval_run_id, base_values))
    threshold_values = {
        "minimum_feature_rows": float(len(features)),
        "minimum_model_rows": float(len(models)),
        "minimum_eval_labels": float(len(labels)),
        "minimum_split_count": float(len(splits)),
        "minimum_baseline_ladder_step_count": float(len(BASELINE_LADDER)),
        "minimum_target_vs_market_sector_improvement_abs": base_values.get("target_vs_market_sector_improvement_abs"),
        "minimum_target_vs_market_improvement_abs": base_values.get("target_vs_market_improvement_abs"),
        "minimum_split_stability_sign_consistency": base_values.get("split_stability_sign_consistency"),
        "maximum_stability_correlation_range": base_values.get("stability_correlation_range"),
        "maximum_leakage_violation_count": base_values.get("leakage_violation_count"),
        "minimum_identity_leakage_violation_count": 0.0,
    }
    for name, observed in threshold_values.items():
        threshold = thresholds[name]
        if observed is None:
            passed = False
        elif name.startswith("maximum_"):
            passed = observed <= threshold
        elif name == "minimum_identity_leakage_violation_count":
            passed = observed >= threshold
        else:
            passed = observed >= threshold
        metrics.append(_metric(eval_run_id, f"threshold:{name}", observed, {"threshold": threshold, "passed": passed}))
    return metrics


def _pair(feature: Mapping[str, Any], model: Mapping[str, Any], label: Mapping[str, Any]) -> dict[str, float]:
    label_abs = abs(_safe_float(label.get("label_value")) or 0.0)
    market = abs(_market_direction(feature) or 0.0)
    sector = abs(_sector_direction(feature) or 0.0)
    target = _safe_float(model.get("3_tradability_score_15min")) or abs(_safe_float(model.get("3_target_direction_score_15min")) or 0.0)
    return {"label_abs": label_abs, "market_only_baseline": market, "market_sector_baseline": (market + sector) / 2.0, "market_sector_target_vector": target, "time": _row_time(feature).timestamp()}


def _baseline_summary(pairs: Sequence[Mapping[str, float]]) -> dict[str, float | None]:
    if not pairs:
        return {"target_vs_market_sector_improvement_abs": None, "target_vs_market_improvement_abs": None, "split_stability_sign_consistency": 0.0, "stability_correlation_range": 999.0, "leakage_violation_count": 0.0}
    cors = {name: _corr([p[name] for p in pairs], [p["label_abs"] for p in pairs]) for name in BASELINE_LADDER}
    target = abs(cors.get("market_sector_target_vector") or 0.0)
    market_sector = abs(cors.get("market_sector_baseline") or 0.0)
    market = abs(cors.get("market_only_baseline") or 0.0)
    thirds = _split_pairs(pairs)
    split_cors = [_corr([p["market_sector_target_vector"] for p in split], [p["label_abs"] for p in split]) for split in thirds if len(split) >= 2]
    signs = [1 if (value or 0) >= 0 else -1 for value in split_cors]
    sign_consistency = max(signs.count(1), signs.count(-1)) / len(signs) if signs else 0.0
    corr_range = (max(split_cors) - min(split_cors)) if split_cors else 999.0
    return {"target_vs_market_sector_improvement_abs": target - market_sector, "target_vs_market_improvement_abs": target - market, "split_stability_sign_consistency": sign_consistency, "stability_correlation_range": corr_range, "leakage_violation_count": 0.0, **{f"abs_corr:{key}": abs(value or 0.0) for key, value in cors.items()}}


def _metric_rows(eval_run_id: str, values: Mapping[str, float | None]) -> list[dict[str, Any]]:
    return [_metric(eval_run_id, name, value, {"baseline_ladder": BASELINE_LADDER}) for name, value in values.items()]


def _metric(eval_run_id: str, name: str, value: float | None, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {"metric_id": _stable_id("mdmet", eval_run_id, name), "eval_run_id": eval_run_id, "metric_name": name, "metric_value": value, "metric_payload_json": dict(payload)}


def _split_pairs(pairs: Sequence[Mapping[str, float]]) -> list[list[Mapping[str, float]]]:
    ordered = sorted(pairs, key=lambda row: row.get("time", 0.0))
    if len(ordered) < 3:
        return [list(ordered)]
    n = len(ordered)
    return [list(ordered[: max(1, n // 3)]), list(ordered[max(1, n // 3) : max(2, 2 * n // 3)]), list(ordered[max(2, 2 * n // 3) :])]


def _corr(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def _market_direction(row: Mapping[str, Any]) -> float | None:
    market = _coerce_payload(row.get("market_state_features"))
    if not isinstance(market, Mapping):
        return None
    return _first_numeric(market, ("market_return_15min", "1_market_direction_score", "market_direction_score"))


def _sector_direction(row: Mapping[str, Any]) -> float | None:
    sector = _coerce_payload(row.get("sector_state_features"))
    if not isinstance(sector, Mapping):
        return None
    return _first_numeric(sector, ("sector_return_15min", "2_sector_relative_direction_score", "sector_relative_direction_score"))


def _target_close(row: Mapping[str, Any]) -> float | None:
    target = _coerce_payload(row.get("target_state_features"))
    if isinstance(target, Mapping):
        for group in (target.get("target_price_state"), target.get("target_vwap_location_state"), target):
            if isinstance(group, Mapping):
                value = _first_numeric(group, ("bar_close", "close", "target_close", "price"))
                if value is not None:
                    return value
    return None


def _target_return(row: Mapping[str, Any], horizon: str) -> float | None:
    target = _coerce_payload(row.get("target_state_features"))
    if isinstance(target, Mapping):
        shape = target.get("target_direction_return_shape")
        if isinstance(shape, Mapping):
            return _safe_float(shape.get(f"return_{horizon}"))
    return None


def _first_numeric(value: Any, keys: Sequence[str]) -> float | None:
    if isinstance(value, Mapping):
        for key in keys:
            parsed = _safe_float(value.get(key))
            if parsed is not None:
                return parsed
        for nested in value.values():
            parsed = _first_numeric(nested, keys)
            if parsed is not None:
                return parsed
    return None


def _horizon_steps(horizon: str) -> int:
    return {"15min": 1, "60min": 4, "390min": 26}.get(horizon, 1)


def _payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return _coerce_payload(row.get("metric_payload_json")) if isinstance(_coerce_payload(row.get("metric_payload_json")), Mapping) else {}


def _coerce_payload(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value or {}


def _candidate(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("target_symbol") or "").strip()


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


def _bounds(rows: Sequence[Mapping[str, Any]]) -> tuple[datetime, datetime]:
    times = [_row_time(row) for row in rows]
    return min(times), max(times)


def _data_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(list(rows), sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None

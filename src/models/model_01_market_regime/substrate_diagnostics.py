"""Read-only substrate diagnostics for Layer 1 promotion readiness.

The diagnostic separates three common promotion blockers:

- source-bar sparsity before feature construction;
- feature lookback / non-null signal coverage;
- model generation alignment against feature snapshot times.

It performs no database work. Runtime wrappers may feed it SQL aggregate rows and
feature/model rows from read-only queries.
"""
from __future__ import annotations

import math
from datetime import datetime
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .generator import SIGNAL_COLUMNS, STATE_OUTPUT_COLUMNS

ET = ZoneInfo("America/New_York")
DEFAULT_MODEL_ID = "market_regime_model"
DEFAULT_MIN_SOURCE_DECISION_DAYS = 252
DEFAULT_MIN_FEATURE_SIGNAL_COVERAGE = 0.30
QUALITY_OUTPUT_COLUMNS = ("1_coverage_score", "1_data_quality_score")
PREDICTIVE_STATE_OUTPUT_COLUMNS = tuple(column for column in STATE_OUTPUT_COLUMNS if column not in QUALITY_OUTPUT_COLUMNS)


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


def _safe_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _row_time(row: Mapping[str, Any], *, preferred: str) -> datetime:
    return _parse_time(row.get(preferred) or row.get("available_time") or row.get("snapshot_time"))


def _stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"count": 0.0, "min": None, "max": None, "mean": None}
    return {
        "count": float(len(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "mean": float(mean(values)),
    }


def _time_bounds(rows: Sequence[Mapping[str, Any]], *, preferred: str) -> dict[str, str | None]:
    if not rows:
        return {"start_time": None, "end_time": None}
    times = [_row_time(row, preferred=preferred) for row in rows]
    return {"start_time": _iso(min(times)), "end_time": _iso(max(times))}


def _count_non_null(row: Mapping[str, Any], columns: Sequence[str]) -> int:
    return sum(1 for column in columns if _safe_float(row.get(column)) is not None)


def _source_summary(source_symbol_rows: Sequence[Mapping[str, Any]], *, min_source_decision_days: int) -> dict[str, Any]:
    rows = [dict(row) for row in source_symbol_rows]
    sparse_symbols = []
    for row in rows:
        decision_days = _safe_int(row.get("decision_day_count"))
        if decision_days < min_source_decision_days:
            sparse_symbols.append(
                {
                    "symbol": str(row.get("symbol") or ""),
                    "timeframe": str(row.get("timeframe") or ""),
                    "decision_day_count": decision_days,
                    "required_decision_day_count": min_source_decision_days,
                    "row_count": _safe_int(row.get("row_count")),
                    "decision_row_count": _safe_int(row.get("decision_row_count")),
                    "start_time": str(row.get("start_time") or "") or None,
                    "end_time": str(row.get("end_time") or "") or None,
                }
            )
    return {
        "symbol_timeframe_count": len(rows),
        "symbol_count": len({str(row.get("symbol") or "") for row in rows if str(row.get("symbol") or "").strip()}),
        "row_count": sum(_safe_int(row.get("row_count")) for row in rows),
        "decision_row_count": sum(_safe_int(row.get("decision_row_count")) for row in rows),
        "sparse_symbol_timeframes": sparse_symbols,
    }


def _feature_summary(feature_rows: Sequence[Mapping[str, Any]], *, min_feature_signal_coverage: float) -> dict[str, Any]:
    rows = [dict(row) for row in feature_rows]
    signal_total = len(SIGNAL_COLUMNS)
    non_null_counts = [_count_non_null(row, SIGNAL_COLUMNS) for row in rows]
    coverage_values = [(count / signal_total) if signal_total else 0.0 for count in non_null_counts]
    low_signal_rows = []
    for row, count, coverage in zip(rows, non_null_counts, coverage_values, strict=False):
        if coverage < min_feature_signal_coverage:
            low_signal_rows.append(
                {
                    "snapshot_time": _iso(_row_time(row, preferred="snapshot_time")),
                    "non_null_signal_count": count,
                    "expected_signal_count": signal_total,
                    "signal_coverage": coverage,
                    "minimum_signal_coverage": min_feature_signal_coverage,
                }
            )
    return {
        "row_count": len(rows),
        **_time_bounds(rows, preferred="snapshot_time"),
        "expected_signal_count": signal_total,
        "non_null_signal_count": _stats([float(value) for value in non_null_counts]),
        "signal_coverage": _stats(coverage_values),
        "low_signal_row_count": len(low_signal_rows),
        "low_signal_rows_sample": low_signal_rows[:20],
    }


def _model_summary(model_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in model_rows]
    state_counts = [_count_non_null(row, STATE_OUTPUT_COLUMNS) for row in rows]
    predictive_counts = [_count_non_null(row, PREDICTIVE_STATE_OUTPUT_COLUMNS) for row in rows]
    coverage_values = [_safe_float(row.get("1_coverage_score")) for row in rows]
    clean_coverage = [value for value in coverage_values if value is not None]
    return {
        "row_count": len(rows),
        **_time_bounds(rows, preferred="available_time"),
        "expected_state_output_count": len(STATE_OUTPUT_COLUMNS),
        "expected_predictive_output_count": len(PREDICTIVE_STATE_OUTPUT_COLUMNS),
        "non_null_state_output_count": _stats([float(value) for value in state_counts]),
        "non_null_predictive_output_count": _stats([float(value) for value in predictive_counts]),
        "coverage_score": _stats(clean_coverage),
        "zero_predictive_output_row_count": sum(1 for value in predictive_counts if value == 0),
    }


def _alignment_summary(feature_rows: Sequence[Mapping[str, Any]], model_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    feature_times = {_iso(_row_time(row, preferred="snapshot_time")) for row in feature_rows}
    model_times = {_iso(_row_time(row, preferred="available_time")) for row in model_rows}
    intersection = feature_times & model_times
    feature_without_model = sorted(feature_times - model_times)
    model_without_feature = sorted(model_times - feature_times)
    return {
        "feature_time_count": len(feature_times),
        "model_time_count": len(model_times),
        "feature_model_intersection_count": len(intersection),
        "feature_without_model_count": len(feature_without_model),
        "model_without_feature_count": len(model_without_feature),
        "feature_model_alignment_rate": (len(intersection) / len(feature_times)) if feature_times else None,
        "feature_without_model_sample": feature_without_model[:20],
        "model_without_feature_sample": model_without_feature[:20],
    }


def diagnose_substrate(
    *,
    source_symbol_rows: Iterable[Mapping[str, Any]],
    feature_rows: Iterable[Mapping[str, Any]],
    model_rows: Iterable[Mapping[str, Any]],
    model_id: str = DEFAULT_MODEL_ID,
    min_source_decision_days: int = DEFAULT_MIN_SOURCE_DECISION_DAYS,
    min_feature_signal_coverage: float = DEFAULT_MIN_FEATURE_SIGNAL_COVERAGE,
) -> dict[str, Any]:
    """Build a read-only Layer 1 substrate diagnostic summary."""

    source_list = [dict(row) for row in source_symbol_rows]
    feature_list = [dict(row) for row in feature_rows]
    model_list = [dict(row) for row in model_rows]
    source = _source_summary(source_list, min_source_decision_days=min_source_decision_days)
    feature = _feature_summary(feature_list, min_feature_signal_coverage=min_feature_signal_coverage)
    model = _model_summary(model_list)
    alignment = _alignment_summary(feature_list, model_list)
    blocker_counts = {
        "source_sparse_symbol_timeframe_count": len(source["sparse_symbol_timeframes"]),
        "feature_low_signal_row_count": feature["low_signal_row_count"],
        "model_feature_missing_alignment_count": alignment["feature_without_model_count"],
        "model_zero_predictive_output_row_count": model["zero_predictive_output_row_count"],
    }
    return {
        "contract_type": "model_01_market_regime_substrate_diagnostic_v1",
        "model_id": model_id,
        "write_policy": "read_only_no_database_write",
        "source_bar_summary": source,
        "feature_summary": feature,
        "model_summary": model,
        "alignment_summary": alignment,
        "blocker_counts": blocker_counts,
        "promotion_readiness_hint": "deferred_until_source_feature_model_substrate_gaps_are_resolved"
        if any(value for value in blocker_counts.values())
        else "substrate_gaps_not_detected_by_this_diagnostic",
    }


__all__ = ["diagnose_substrate"]

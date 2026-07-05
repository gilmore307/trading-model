"""Builder for tradable-time return distribution surfaces.

The current implementation models one market-calendar family first:
regular-session US equity bars. It keeps raw bars on their native 1-minute
source grain, samples point-in-time anchors at a 10-minute tradable-time grid,
expands each anchor to an equal-step target grid through a bounded future
trading window, and fits a smooth return quantile/CDF surface over
``tau_trading_minutes``.

Open/close/overnight effects remain target-row context and validation slices.
They are not separate label heads.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")
SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)
SESSION_MINUTES = 390
DEFAULT_QUANTILE_LEVELS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
DEFAULT_CDF_THRESHOLDS = (-0.05, -0.02, 0.0, 0.02, 0.05)


@dataclass(frozen=True)
class BucketClose:
    """Last available close inside one regular-session bucket."""

    symbol: str
    session_date: date
    bucket_end_minute: int
    timestamp: datetime
    close: float


@dataclass(frozen=True)
class TargetLabelRow:
    """One PIT anchor to one future tradable-time target label."""

    symbol: str
    anchor_time: datetime
    target_time: datetime
    anchor_session_date: date
    target_session_date: date
    anchor_bucket_end_minute: int
    target_bucket_end_minute: int
    tau_trading_minutes: int
    tau_calendar_minutes: float
    session_gap_count: int
    crosses_session_gap: bool
    target_minutes_since_open: int
    target_minutes_to_close: int
    target_near_open: bool
    target_near_close: bool
    return_label: float

    def slice_flags(self) -> dict[str, bool]:
        return {
            "all": True,
            "intraday": not self.crosses_session_gap,
            "crosses_session_gap": self.crosses_session_gap,
            "target_near_open": self.target_near_open,
            "target_near_close": self.target_near_close,
            "one_session_gap": self.session_gap_count == 1,
            "two_plus_session_gaps": self.session_gap_count >= 2,
        }


@dataclass(frozen=True)
class DistributionSurfaceResult:
    """Fitted surface and validation diagnostics."""

    quantile_levels: tuple[float, ...]
    cdf_thresholds: tuple[float, ...]
    horizon_axis_minutes: tuple[int, ...]
    train_horizon_axis_minutes: tuple[int, ...]
    validation_horizon_axis_minutes: tuple[int, ...]
    surface_quantiles: dict[int, dict[str, float]]
    cdf_rows: list[dict[str, Any]]
    validation_rows: list[dict[str, Any]]
    slice_validation: dict[str, dict[str, Any]]
    fit_metadata: dict[str, Any]


def bucket_regular_session_closes(
    rows: Iterable[Mapping[str, Any]],
    *,
    bucket_minutes: int = 10,
    symbol: str | None = None,
) -> list[BucketClose]:
    """Convert PIT bars to one close per regular-session bucket."""

    latest_by_bucket: dict[tuple[str, date, int], BucketClose] = {}
    for row in rows:
        ts = row["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ET)
        local = ts.astimezone(ET)
        bucket_end = _bucket_end_minute(local, bucket_minutes)
        if bucket_end is None or bucket_end <= 0 or bucket_end > SESSION_MINUTES:
            continue
        close = float(row.get("bar_close") or row.get("close") or 0.0)
        if close <= 0:
            continue
        row_symbol = str(symbol or row.get("symbol") or "").upper()
        key = (row_symbol, local.date(), bucket_end)
        candidate = BucketClose(row_symbol, local.date(), bucket_end, local, close)
        current = latest_by_bucket.get(key)
        if current is None or candidate.timestamp > current.timestamp:
            latest_by_bucket[key] = candidate
    return sorted(latest_by_bucket.values(), key=lambda item: (item.symbol, item.session_date, item.bucket_end_minute))


def build_tradable_time_label_rows(
    closes: Sequence[BucketClose],
    *,
    anchor_minutes: int = 10,
    max_trading_minutes: int = 3 * SESSION_MINUTES,
    near_open_minutes: int = 30,
    near_close_minutes: int = 30,
) -> list[TargetLabelRow]:
    """Expand equal-step tradable-time target labels from PIT anchors."""

    by_symbol: dict[str, list[BucketClose]] = defaultdict(list)
    for close in closes:
        by_symbol[close.symbol].append(close)
    output: list[TargetLabelRow] = []
    max_steps = max_trading_minutes // anchor_minutes
    for symbol, symbol_closes in by_symbol.items():
        symbol_closes = sorted(symbol_closes, key=lambda item: (item.session_date, item.bucket_end_minute))
        session_ordinals = {
            session_date: ordinal
            for ordinal, session_date in enumerate(sorted({item.session_date for item in symbol_closes}))
        }
        for origin_index, origin in enumerate(symbol_closes):
            if origin.bucket_end_minute % anchor_minutes:
                continue
            for step in range(1, max_steps + 1):
                target_index = origin_index + step
                if target_index >= len(symbol_closes):
                    break
                target = symbol_closes[target_index]
                session_gap_count = session_ordinals[target.session_date] - session_ordinals[origin.session_date]
                output.append(
                    TargetLabelRow(
                        symbol=symbol,
                        anchor_time=origin.timestamp,
                        target_time=target.timestamp,
                        anchor_session_date=origin.session_date,
                        target_session_date=target.session_date,
                        anchor_bucket_end_minute=origin.bucket_end_minute,
                        target_bucket_end_minute=target.bucket_end_minute,
                        tau_trading_minutes=step * anchor_minutes,
                        tau_calendar_minutes=(target.timestamp - origin.timestamp).total_seconds() / 60.0,
                        session_gap_count=session_gap_count,
                        crosses_session_gap=session_gap_count > 0,
                        target_minutes_since_open=target.bucket_end_minute,
                        target_minutes_to_close=SESSION_MINUTES - target.bucket_end_minute,
                        target_near_open=target.bucket_end_minute <= near_open_minutes,
                        target_near_close=(SESSION_MINUTES - target.bucket_end_minute) <= near_close_minutes,
                        return_label=target.close / origin.close - 1.0,
                    )
                )
    return output


def fit_tradable_time_distribution_surface(
    label_rows: Sequence[TargetLabelRow],
    *,
    quantile_levels: Sequence[float] = DEFAULT_QUANTILE_LEVELS,
    cdf_thresholds: Sequence[float] = DEFAULT_CDF_THRESHOLDS,
    validation_stride: int = 2,
    polynomial_degree: int = 5,
    fit_mode: str = "context",
) -> DistributionSurfaceResult:
    """Fit and validate a smooth quantile/CDF surface over tradable time."""

    if fit_mode not in {"baseline", "context"}:
        raise ValueError(f"unsupported fit_mode: {fit_mode!r}")
    returns_by_tau: dict[int, list[float]] = defaultdict(list)
    for row in label_rows:
        returns_by_tau[row.tau_trading_minutes].append(row.return_label)
    if len(returns_by_tau) < 4:
        raise ValueError("at least four target horizons are required")
    taus = tuple(sorted(returns_by_tau))
    train_taus = tuple(tau for index, tau in enumerate(taus) if index % validation_stride != validation_stride - 1)
    validation_taus = tuple(tau for tau in taus if tau not in train_taus)
    if len(train_taus) < 2:
        train_taus = taus
        validation_taus = ()

    empirical = {
        tau: _empirical_quantiles(returns_by_tau[tau], quantile_levels)
        for tau in taus
    }
    x_train = _fit_axis(train_taus)
    x_all = _fit_axis(taus)
    surface: dict[int, dict[str, float]] = {tau: dict(empirical[tau]) for tau in taus}
    degree = max(0, min(polynomial_degree, len(train_taus) - 1))
    context_model: dict[str, Any] | None = None
    if fit_mode == "baseline":
        for key in _quantile_keys(quantile_levels):
            y_train = np.asarray([empirical[tau][key] for tau in train_taus], dtype=float)
            if degree == 0:
                y_pred = np.repeat(y_train[0], len(taus))
            else:
                coeff = np.polyfit(x_train, y_train, deg=degree)
                y_pred = np.polyval(coeff, x_all)
            for tau, value in zip(taus, y_pred):
                surface[tau][key] = float(value)
    else:
        context_model = _fit_context_quantile_model(
            label_rows,
            train_taus=train_taus,
            quantile_levels=quantile_levels,
            degree=degree,
        )
        for tau in taus:
            surface[tau] = _predict_context_quantiles_for_values(
                tau=tau,
                context_values={name: 0.0 for name in context_model["context_feature_names"]},
                levels=quantile_levels,
                context_model=context_model,
            )

    crossing_repairs = _repair_crossing(surface, quantile_levels)
    validation_rows = _validation_rows(
        returns_by_tau,
        surface,
        label_rows,
        validation_taus,
        quantile_levels,
        context_model,
    )
    cdf_rows = _cdf_rows(surface, cdf_thresholds, quantile_levels)
    slice_validation = _slice_validation(label_rows, surface, quantile_levels, validation_taus, context_model)
    return DistributionSurfaceResult(
        quantile_levels=tuple(float(level) for level in quantile_levels),
        cdf_thresholds=tuple(float(threshold) for threshold in cdf_thresholds),
        horizon_axis_minutes=taus,
        train_horizon_axis_minutes=train_taus,
        validation_horizon_axis_minutes=validation_taus,
        surface_quantiles=surface,
        cdf_rows=cdf_rows,
        validation_rows=validation_rows,
        slice_validation=slice_validation,
        fit_metadata={
            "fit_type": (
                "single_context_conditioned_shape_constrained_tradable_time_quantile_surface"
                if fit_mode == "context"
                else "single_tradable_time_quantile_polynomial"
            ),
            "fit_x": "sqrt(tau_trading_minutes)",
            "polynomial_degree": degree,
            "quantile_crossing_repairs": crossing_repairs,
            "event_context_role": (
                "target_row_features_in_same_surface_function"
                if fit_mode == "context"
                else "target_row_features_and_validation_slices"
            ),
            **({"context_model": _context_model_metadata(context_model)} if context_model else {}),
        },
    )


def summarize_surface_result(
    *,
    symbol: str,
    source_table: str,
    source_timeframe: str | None,
    source_range: Mapping[str, str],
    anchor_minutes: int,
    bar_rows_loaded: int,
    bucket_close_count: int,
    label_rows: Sequence[TargetLabelRow],
    result: DistributionSurfaceResult,
    surface_csv: str,
) -> dict[str, Any]:
    """Build a stable JSON summary for one surface build."""

    validation_errors = [row["abs_quantile_error"] for row in result.validation_rows]
    coverage_errors = [row["abs_coverage_error"] for row in result.validation_rows]
    sessions = {row.anchor_session_date for row in label_rows}
    return {
        "contract_type": "tradable_time_return_distribution_surface_summary",
        "symbol": symbol.upper(),
        "source_table": source_table,
        "source_timeframe": source_timeframe,
        "source_range": dict(source_range),
        "anchor_minutes": anchor_minutes,
        "target_grid": {
            "grid_type": "equal_step_tradable_time",
            "max_tau_trading_minutes": max(result.horizon_axis_minutes),
            "horizon_count": len(result.horizon_axis_minutes),
            "horizon_axis_minutes": list(result.horizon_axis_minutes),
        },
        "sample": {
            "bar_rows_loaded": bar_rows_loaded,
            "bucket_close_count": bucket_close_count,
            "label_row_count": len(label_rows),
            "session_count": len(sessions),
        },
        "fit": result.fit_metadata | {
            "train_horizon_axis_minutes": list(result.train_horizon_axis_minutes),
            "validation_horizon_axis_minutes": list(result.validation_horizon_axis_minutes),
        },
        "evaluation": {
            "mean_abs_quantile_error": float(np.mean(validation_errors)) if validation_errors else None,
            "max_abs_quantile_error": float(np.max(validation_errors)) if validation_errors else None,
            "mean_abs_coverage_error": float(np.mean(coverage_errors)) if coverage_errors else None,
            "max_abs_coverage_error": float(np.max(coverage_errors)) if coverage_errors else None,
            "cdf_monotone_failures": sum(1 for row in result.cdf_rows if not row["cdf_monotone"]),
            "slice_validation": result.slice_validation,
        },
        "surface_csv": surface_csv,
        "side_effects": {
            "provider_call_performed": False,
            "broker_execution_performed": False,
            "account_mutation_performed": False,
            "model_activation_performed": False,
            "sql_mutation_performed": False,
            "storage_source_mutation_performed": False,
        },
    }


def _regular_session_minute(ts: datetime) -> int | None:
    local = ts.astimezone(ET)
    session_start = datetime.combine(local.date(), SESSION_OPEN, tzinfo=ET)
    session_end = datetime.combine(local.date(), SESSION_CLOSE, tzinfo=ET)
    if local < session_start or local > session_end:
        return None
    return int((local - session_start).total_seconds() // 60)


def _bucket_end_minute(ts: datetime, bucket_minutes: int) -> int | None:
    minute = _regular_session_minute(ts)
    if minute is None:
        return None
    if minute >= SESSION_MINUTES:
        return SESSION_MINUTES
    return ((minute // bucket_minutes) + 1) * bucket_minutes


def _fit_axis(taus: Sequence[int]) -> np.ndarray:
    return np.sqrt(np.asarray(taus, dtype=float))


def _quantile_keys(levels: Sequence[float]) -> list[str]:
    return [f"p{int(level * 100):02d}" for level in levels]


def _empirical_quantiles(values: Sequence[float], levels: Sequence[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {
        key: float(np.quantile(arr, level))
        for key, level in zip(_quantile_keys(levels), levels)
    }


def _repair_crossing(surface: dict[int, dict[str, float]], levels: Sequence[float]) -> int:
    keys = _quantile_keys(levels)
    repairs = 0
    for tau in sorted(surface):
        values = [surface[tau][key] for key in keys]
        repaired = np.maximum.accumulate(values)
        repairs += sum(1 for original, new in zip(values, repaired) if abs(original - new) > 1e-12)
        for key, value in zip(keys, repaired):
            surface[tau][key] = float(value)
    return repairs


def _context_feature_names() -> tuple[str, ...]:
    return (
        "crosses_session_gap",
        "target_near_open",
        "target_near_close",
        "one_session_gap",
        "two_plus_session_gaps",
        "near_open_cross_gap",
        "near_close_intraday",
    )


def _context_values(row: TargetLabelRow) -> dict[str, float]:
    crosses = float(row.crosses_session_gap)
    near_open = float(row.target_near_open)
    near_close = float(row.target_near_close)
    one_gap = float(row.session_gap_count == 1)
    two_plus = float(row.session_gap_count >= 2)
    return {
        "crosses_session_gap": crosses,
        "target_near_open": near_open,
        "target_near_close": near_close,
        "one_session_gap": one_gap,
        "two_plus_session_gaps": two_plus,
        "near_open_cross_gap": float(row.target_near_open and row.crosses_session_gap),
        "near_close_intraday": float(row.target_near_close and not row.crosses_session_gap),
    }


def _context_signature(row: TargetLabelRow, names: Sequence[str]) -> tuple[int, ...]:
    values = _context_values(row)
    return tuple(int(values[name]) for name in names)


def _feature_names(degree: int, context_names: Sequence[str]) -> list[str]:
    names = [f"tau_sqrt_power_{power}" for power in range(degree + 1)]
    names.extend(context_names)
    names.extend(f"{name}_x_sqrt_tau" for name in context_names)
    return names


def _design_vector_for_context(
    *,
    tau: int,
    degree: int,
    context_values: Mapping[str, float],
    feature_names: Sequence[str],
) -> np.ndarray:
    sqrt_tau = math.sqrt(float(tau))
    powers = {f"tau_sqrt_power_{power}": sqrt_tau**power for power in range(degree + 1)}
    values: dict[str, float] = dict(powers)
    for name, value in context_values.items():
        values[name] = float(value)
        values[f"{name}_x_sqrt_tau"] = float(value) * sqrt_tau
    return np.asarray([values.get(name, 0.0) for name in feature_names], dtype=float)


def _fit_context_quantile_model(
    label_rows: Sequence[TargetLabelRow],
    *,
    train_taus: Sequence[int],
    quantile_levels: Sequence[float],
    degree: int,
    min_cell_count: int = 30,
    ridge_lambda: float = 1e-5,
) -> dict[str, Any]:
    context_names = _context_feature_names()
    feature_names = _feature_names(degree, context_names)
    train_tau_set = set(train_taus)
    groups: dict[tuple[int, tuple[int, ...]], list[float]] = defaultdict(list)
    for row in label_rows:
        if row.tau_trading_minutes not in train_tau_set:
            continue
        groups[(row.tau_trading_minutes, _context_signature(row, context_names))].append(row.return_label)

    observations: list[tuple[int, tuple[int, ...], int, dict[str, float]]] = []
    for (tau, signature), values in sorted(groups.items()):
        if len(values) < min_cell_count:
            continue
        observations.append((tau, signature, len(values), _empirical_quantiles(values, quantile_levels)))
    if len(observations) < len(feature_names):
        raise ValueError("not enough context cells to fit context-conditioned surface")

    x_rows: list[np.ndarray] = []
    weights: list[float] = []
    for tau, signature, count, _ in observations:
        context_values = {name: float(value) for name, value in zip(context_names, signature)}
        x_rows.append(
            _design_vector_for_context(
                tau=tau,
                degree=degree,
                context_values=context_values,
                feature_names=feature_names,
            )
        )
        weights.append(math.sqrt(count))
    x = np.vstack(x_rows)
    w = np.asarray(weights, dtype=float)
    x_weighted = x * w[:, None]
    penalty = np.sqrt(ridge_lambda) * np.eye(len(feature_names))
    penalty[0, 0] = 0.0
    x_augmented = np.vstack([x_weighted, penalty])

    keys = _quantile_keys(quantile_levels)
    base_key = keys[0]
    base_y = np.asarray([quantiles[base_key] for _, _, _, quantiles in observations], dtype=float)
    base_augmented = np.concatenate([base_y * w, np.zeros(len(feature_names), dtype=float)])
    base_coefficients, *_ = np.linalg.lstsq(x_augmented, base_augmented, rcond=None)

    spacing_coefficients: dict[str, np.ndarray] = {}
    for lower_key, upper_key in zip(keys, keys[1:]):
        spacing_y = np.asarray(
            [
                max(quantiles[upper_key] - quantiles[lower_key], 1e-8)
                for _, _, _, quantiles in observations
            ],
            dtype=float,
        )
        spacing_augmented = np.concatenate([spacing_y * w, np.zeros(len(feature_names), dtype=float)])
        coeff, *_ = np.linalg.lstsq(x_augmented, spacing_augmented, rcond=None)
        spacing_coefficients[f"{lower_key}_to_{upper_key}"] = coeff

    return {
        "degree": degree,
        "context_feature_names": list(context_names),
        "feature_names": feature_names,
        "base_quantile_key": base_key,
        "base_coefficients": base_coefficients,
        "spacing_coefficients": spacing_coefficients,
        "spacing_link": "positive_floor_adjacent_quantile_spacing",
        "observation_count": len(observations),
        "min_cell_count": min_cell_count,
        "ridge_lambda": ridge_lambda,
    }


def _context_model_metadata(context_model: Mapping[str, Any] | None) -> dict[str, Any]:
    if not context_model:
        return {}
    return {
        "context_feature_names": list(context_model["context_feature_names"]),
        "degree": context_model["degree"],
        "feature_count": len(context_model["feature_names"]),
        "shape_constraint": "adjacent_quantile_spacings_are_positive_by_construction",
        "base_quantile_key": context_model["base_quantile_key"],
        "spacing_link": context_model["spacing_link"],
        "observation_count": context_model["observation_count"],
        "min_cell_count": context_model["min_cell_count"],
        "ridge_lambda": context_model["ridge_lambda"],
        "coefficient_schema": "omitted_from_summary",
    }


def _predict_context_quantiles_for_values(
    *,
    tau: int,
    context_values: Mapping[str, float],
    levels: Sequence[float],
    context_model: Mapping[str, Any],
) -> dict[str, float]:
    design = _design_vector_for_context(
        tau=tau,
        degree=int(context_model["degree"]),
        context_values=context_values,
        feature_names=context_model["feature_names"],
    )
    keys = _quantile_keys(levels)
    values = [float(np.dot(context_model["base_coefficients"], design))]
    for lower_key, upper_key in zip(keys, keys[1:]):
        raw_spacing = float(
            np.dot(context_model["spacing_coefficients"][f"{lower_key}_to_{upper_key}"], design)
        )
        spacing = max(1e-8, raw_spacing)
        values.append(values[-1] + spacing)
    return {key: float(value) for key, value in zip(keys, values)}


def _predict_quantiles(
    row: TargetLabelRow,
    surface: Mapping[int, Mapping[str, float]],
    levels: Sequence[float],
    context_model: Mapping[str, Any] | None,
) -> dict[str, float] | None:
    base = surface.get(row.tau_trading_minutes)
    if base is None:
        return None
    if not context_model:
        return dict(base)
    return _predict_context_quantiles_for_values(
        tau=row.tau_trading_minutes,
        context_values=_context_values(row),
        levels=levels,
        context_model=context_model,
    )


def _prediction_cache_key(
    row: TargetLabelRow,
    context_model: Mapping[str, Any] | None,
) -> tuple[Any, ...]:
    if not context_model:
        return (row.tau_trading_minutes,)
    return (
        row.tau_trading_minutes,
        _context_signature(row, context_model["context_feature_names"]),
    )


def _cdf_from_quantiles(value: float, quantiles: Mapping[str, float], levels: Sequence[float]) -> float:
    points = [(0.0, -math.inf)]
    for key, level in zip(_quantile_keys(levels), levels):
        points.append((level, float(quantiles[key])))
    points.append((1.0, math.inf))
    for (p0, x0), (p1, x1) in zip(points, points[1:]):
        if value <= x1:
            if not math.isfinite(x0):
                return float(p1)
            if not math.isfinite(x1):
                return float(p0)
            if abs(x1 - x0) < 1e-12:
                return float((p0 + p1) / 2.0)
            return float(p0 + (p1 - p0) * ((value - x0) / (x1 - x0)))
    return 1.0


def _validation_rows(
    returns_by_tau: Mapping[int, Sequence[float]],
    surface: Mapping[int, Mapping[str, float]],
    label_rows: Sequence[TargetLabelRow],
    validation_taus: Sequence[int],
    levels: Sequence[float],
    context_model: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = _quantile_keys(levels)
    empirical = {
        tau: _empirical_quantiles(returns_by_tau[tau], levels)
        for tau in validation_taus
        if tau in returns_by_tau
    }
    prediction_cache: dict[tuple[Any, ...], dict[str, float] | None] = {}
    for tau in validation_taus:
        tau_rows = [row for row in label_rows if row.tau_trading_minutes == tau]
        values = returns_by_tau.get(tau, ())
        if not values or not tau_rows:
            continue
        for key, level in zip(keys, levels):
            predicted: list[float] = []
            hits = 0
            for row in tau_rows:
                cache_key = _prediction_cache_key(row, context_model)
                if cache_key not in prediction_cache:
                    prediction_cache[cache_key] = _predict_quantiles(row, surface, levels, context_model)
                quantiles = prediction_cache[cache_key]
                if quantiles is None:
                    continue
                predicted.append(quantiles[key])
                if row.return_label <= quantiles[key]:
                    hits += 1
            if not predicted:
                continue
            smooth_quantile = float(np.mean(predicted))
            empirical_coverage = hits / len(predicted)
            rows.append(
                {
                    "tau_trading_minutes": tau,
                    "quantile": key,
                    "target_probability": float(level),
                    "smooth_quantile": smooth_quantile,
                    "empirical_quantile": empirical[tau][key],
                    "abs_quantile_error": abs(smooth_quantile - empirical[tau][key]),
                    "empirical_coverage": empirical_coverage,
                    "abs_coverage_error": abs(empirical_coverage - level),
                }
            )
    return rows


def _cdf_rows(
    surface: Mapping[int, Mapping[str, float]],
    thresholds: Sequence[float],
    levels: Sequence[float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tau, quantiles in sorted(surface.items()):
        probs = [
            _cdf_from_quantiles(threshold, quantiles, levels)
            for threshold in thresholds
        ]
        rows.append(
            {
                "tau_trading_minutes": tau,
                **{f"cdf_le_{threshold:+.2%}": prob for threshold, prob in zip(thresholds, probs)},
                "cdf_monotone": all(left <= right + 1e-12 for left, right in zip(probs, probs[1:])),
            }
        )
    return rows


def _slice_validation(
    label_rows: Sequence[TargetLabelRow],
    surface: Mapping[int, Mapping[str, float]],
    levels: Sequence[float],
    validation_taus: Sequence[int],
    context_model: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    by_slice: dict[str, list[TargetLabelRow]] = defaultdict(list)
    validation_tau_set = set(validation_taus)
    for row in label_rows:
        if validation_tau_set and row.tau_trading_minutes not in validation_tau_set:
            continue
        for name, enabled in row.slice_flags().items():
            if enabled:
                by_slice[name].append(row)
    output: dict[str, dict[str, Any]] = {}
    for name, rows in sorted(by_slice.items()):
        if not rows:
            continue
        errors: list[float] = []
        prediction_cache: dict[tuple[Any, ...], dict[str, float] | None] = {}
        for key, level in zip(_quantile_keys(levels), levels):
            hits = 0
            total = 0
            for row in rows:
                cache_key = _prediction_cache_key(row, context_model)
                if cache_key not in prediction_cache:
                    prediction_cache[cache_key] = _predict_quantiles(row, surface, levels, context_model)
                quantiles = prediction_cache[cache_key]
                if not quantiles:
                    continue
                total += 1
                if row.return_label <= quantiles[key]:
                    hits += 1
            if total:
                errors.append(abs(hits / total - level))
        output[name] = {
            "sample_count": len(rows),
            "mean_abs_coverage_error": float(np.mean(errors)) if errors else None,
            "max_abs_coverage_error": float(np.max(errors)) if errors else None,
        }
    return output

"""Continuous MarketRegimeModel V1 state-vector generator.

The generator converts point-in-time rows from
``trading_derived.derived_01_market_regime`` into the model output table
``trading_model.model_01_market_regime``. V1 intentionally avoids clustering,
hard state ids, supervised labels, and human-readable regime labels. The primary
output is a bounded continuous market-condition vector keyed by ``available_time``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUTPUT_COLUMNS = [
    "available_time",
    "trend_factor",
    "volatility_stress_factor",
    "correlation_stress_factor",
    "credit_stress_factor",
    "rate_pressure_factor",
    "dollar_pressure_factor",
    "commodity_pressure_factor",
    "sector_rotation_factor",
    "breadth_factor",
    "risk_appetite_factor",
    "transition_pressure",
    "data_quality_score",
]
FACTOR_COLUMNS = [column for column in OUTPUT_COLUMNS if column not in {"available_time", "transition_pressure", "data_quality_score"}]


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


def _parse_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("available_time or snapshot_time is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _row_available_time(row: Mapping[str, Any]) -> datetime:
    return _parse_time(row.get("available_time") or row.get("snapshot_time"))


def _bounded(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return math.tanh(mean(values) / 2.0)


def _bounded_abs(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return math.tanh(mean(abs(value) for value in values) / 2.0)


@dataclass(frozen=True)
class Signal:
    column: str
    direction: float = 1.0


@dataclass(frozen=True)
class FactorSpec:
    name: str
    signals: tuple[Signal, ...]
    reducer: Callable[[Sequence[float]], float | None] = _bounded


class RollingZScore:
    def __init__(self, *, lookback: int = 120, min_history: int = 3) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        if min_history < 1:
            raise ValueError("min_history must be positive")
        self.lookback = lookback
        self.min_history = min_history
        self.history: dict[str, list[float]] = {}

    def zscore(self, column: str, value: float | None) -> float | None:
        if value is None:
            return None
        values = self.history.get(column, [])[-self.lookback :]
        if len(values) < self.min_history:
            return None
        sigma = pstdev(values)
        if sigma == 0:
            return 0.0
        return (value - mean(values)) / sigma

    def update(self, row: Mapping[str, Any], columns: Iterable[str]) -> None:
        for column in columns:
            value = _safe_float(row.get(column))
            if value is None:
                continue
            values = self.history.setdefault(column, [])
            values.append(value)
            if len(values) > self.lookback:
                del values[:-self.lookback]


def _signals(*columns: str, direction: float = 1.0) -> tuple[Signal, ...]:
    return tuple(Signal(column, direction) for column in columns)


def _symbol_signals(symbols: Sequence[str], suffixes: Sequence[str], *, direction: float = 1.0) -> tuple[Signal, ...]:
    return tuple(Signal(f"{symbol}_{suffix}", direction) for symbol in symbols for suffix in suffixes)


BROAD_RISK_SYMBOLS = ("spy", "qqq", "iwm", "dia", "rsp")
COMMODITY_SYMBOLS = ("dbc", "gld", "slv", "uso", "dba", "cper")

FACTOR_SPECS = [
    FactorSpec(
        "trend_factor",
        _symbol_signals(
            BROAD_RISK_SYMBOLS,
            ("return_5d", "return_20d", "distance_to_ma20", "distance_to_ma50", "ma20_slope_5d", "ma_alignment_score"),
        ),
    ),
    FactorSpec(
        "volatility_stress_factor",
        _symbol_signals(
            BROAD_RISK_SYMBOLS + ("vixy",),
            (
                "realized_vol_20d",
                "realized_vol_20d_percentile_252d",
                "realized_vol_20d_zscore_252d",
                "ewma_vol",
                "atr_pct_14d",
            ),
        )
        + _symbol_signals(("vixy",), ("return_5d", "return_20d", "distance_to_ma20", "ma_alignment_score")),
    ),
    FactorSpec(
        "correlation_stress_factor",
        _signals(
            "market_state_avg_abs_return_corr_20d",
            "market_state_avg_abs_return_corr_60d",
            "market_state_avg_return_corr_20d",
            "market_state_avg_return_corr_60d",
        ),
    ),
    FactorSpec(
        "credit_stress_factor",
        _signals("hyg_lqd_30m", "hyg_lqd_distance_to_ma20", "hyg_lqd_ma_alignment_score", direction=-1.0)
        + _signals("hyg_lqd_realized_vol_20d_ratio"),
    ),
    FactorSpec(
        "rate_pressure_factor",
        _signals(
            "tlt_shy_30m",
            "tlt_shy_distance_to_ma20",
            "tlt_shy_ma_alignment_score",
            "ief_shy_30m",
            "ief_shy_distance_to_ma20",
            "ief_shy_ma_alignment_score",
            direction=-1.0,
        ),
    ),
    FactorSpec(
        "dollar_pressure_factor",
        _signals("uup_spy_30m", "uup_spy_distance_to_ma20", "uup_spy_ma_alignment_score")
        + _symbol_signals(("uup",), ("return_5d", "return_20d", "distance_to_ma20", "ma_alignment_score")),
    ),
    FactorSpec(
        "commodity_pressure_factor",
        _symbol_signals(COMMODITY_SYMBOLS, ("return_5d", "return_20d", "distance_to_ma20", "ma_alignment_score"))
        + _signals("gld_spy_30m", "xle_spy_30m", "uso_dbc_30m", "cper_dbc_30m"),
    ),
    FactorSpec(
        "sector_rotation_factor",
        _signals("sector_observation_distance_to_ma20_dispersion", "sector_observation_return_20d_dispersion")
        + _signals(
            "xlk_spy_30m",
            "xlf_spy_30m",
            "xle_spy_30m",
            "xlv_spy_30m",
            "xly_xlp_30m",
            "smh_xlk_30m",
        ),
        reducer=_bounded_abs,
    ),
    FactorSpec(
        "breadth_factor",
        _signals(
            "sector_observation_positive_return_1d_pct",
            "sector_observation_positive_return_5d_pct",
            "sector_observation_above_ma20_pct",
            "sector_observation_above_ma50_pct",
            "sector_observation_above_ma200_pct",
            "rsp_spy_30m",
            "rsp_spy_distance_to_ma20",
        ),
    ),
    FactorSpec(
        "risk_appetite_factor",
        _signals(
            "qqq_spy_30m",
            "iwm_spy_30m",
            "rsp_spy_30m",
            "hyg_lqd_30m",
            "xly_xlp_30m",
            "bitw_spy_30m",
        )
        + _signals("tlt_spy_30m", "gld_spy_30m", "uup_spy_30m", "vixy_spy_30m", direction=-1.0),
    ),
]

SPEC_BY_NAME = {spec.name: spec for spec in FACTOR_SPECS}
SIGNAL_COLUMNS = sorted({signal.column for spec in FACTOR_SPECS for signal in spec.signals})


def generate_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    *,
    lookback: int = 120,
    min_history: int = 3,
) -> list[dict[str, Any]]:
    rows = sorted(feature_rows, key=_row_available_time)
    scaler = RollingZScore(lookback=lookback, min_history=min_history)
    output_rows: list[dict[str, Any]] = []
    previous_factors: dict[str, float] | None = None

    for feature_row in rows:
        output = generate_row(feature_row, scaler=scaler, previous_factors=previous_factors)
        output_rows.append(output)
        scaler.update(feature_row, SIGNAL_COLUMNS)
        previous_factors = {column: output[column] for column in FACTOR_COLUMNS if output.get(column) is not None}

    return output_rows


def generate_row(
    feature_row: Mapping[str, Any],
    *,
    scaler: RollingZScore,
    previous_factors: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {"available_time": _row_available_time(feature_row).isoformat()}
    factor_values: dict[str, float] = {}
    observed_signal_columns: set[str] = set()
    total_signals = len(SIGNAL_COLUMNS)

    for spec in FACTOR_SPECS:
        zscores: list[float] = []
        for signal in spec.signals:
            value = _safe_float(feature_row.get(signal.column))
            if value is None:
                continue
            observed_signal_columns.add(signal.column)
            zscore = scaler.zscore(signal.column, value)
            if zscore is not None:
                zscores.append(signal.direction * zscore)
        factor = spec.reducer(zscores)
        output[spec.name] = factor
        if factor is not None:
            factor_values[spec.name] = factor

    output["transition_pressure"] = _transition_pressure(factor_values, previous_factors)
    output["data_quality_score"] = len(observed_signal_columns) / total_signals if total_signals else None
    return output


def _transition_pressure(current: Mapping[str, float], previous: Mapping[str, float] | None) -> float | None:
    if not previous:
        return None
    deltas = [abs(value - previous[name]) for name, value in current.items() if name in previous]
    if not deltas:
        return None
    return math.tanh(mean(deltas) * 2.0)

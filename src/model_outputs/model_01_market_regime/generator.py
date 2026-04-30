"""Continuous MarketRegimeModel V1 state-vector generator.

The generator converts point-in-time rows from
``trading_derived.derived_01_market_regime`` into the model output table
``trading_model.model_01_market_regime``. V1 intentionally avoids clustering,
hard state ids, supervised labels, and human-readable regime labels. The primary
output is a bounded continuous market-condition vector keyed by ``available_time``.

Factor membership, signal direction, and reducer choice live in
``config/factor_specs.toml`` so the model contract can evolve without editing
execution code.
"""
from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "factor_specs.toml"


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


REDUCERS: dict[str, Callable[[Sequence[float]], float | None]] = {
    "bounded_mean": _bounded,
    "bounded_abs_mean": _bounded_abs,
}


@dataclass(frozen=True)
class Signal:
    column: str
    direction: float = 1.0


@dataclass(frozen=True)
class FactorSpec:
    name: str
    signals: tuple[Signal, ...]
    reducer: Callable[[Sequence[float]], float | None] = _bounded


def _signal_group_columns(group: Mapping[str, Any], *, factor_name: str) -> list[str]:
    columns = group.get("columns")
    symbols = group.get("symbols")
    suffixes = group.get("suffixes")

    if columns and (symbols or suffixes):
        raise ValueError(f"factor {factor_name!r} group must use columns or symbols/suffixes, not both")
    if columns:
        if not isinstance(columns, list) or not all(isinstance(column, str) and column for column in columns):
            raise ValueError(f"factor {factor_name!r} columns must be a non-empty string list")
        return list(columns)
    if symbols or suffixes:
        if not isinstance(symbols, list) or not all(isinstance(symbol, str) and symbol for symbol in symbols):
            raise ValueError(f"factor {factor_name!r} symbols must be a non-empty string list")
        if not isinstance(suffixes, list) or not all(isinstance(suffix, str) and suffix for suffix in suffixes):
            raise ValueError(f"factor {factor_name!r} suffixes must be a non-empty string list")
        return [f"{symbol}_{suffix}" for symbol in symbols for suffix in suffixes]
    raise ValueError(f"factor {factor_name!r} group must define columns or symbols/suffixes")


def load_factor_specs(path: str | Path = DEFAULT_CONFIG_PATH) -> tuple[FactorSpec, ...]:
    config_path = Path(path)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    factor_rows = config.get("factors")
    if not isinstance(factor_rows, list) or not factor_rows:
        raise ValueError(f"factor config {config_path} must define at least one [[factors]] entry")

    specs: list[FactorSpec] = []
    seen_names: set[str] = set()
    for factor in factor_rows:
        if not isinstance(factor, dict):
            raise ValueError("factor config entries must be tables")
        name = factor.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("factor config entry missing non-empty name")
        if name in seen_names:
            raise ValueError(f"duplicate factor name: {name}")
        seen_names.add(name)

        reducer_name = factor.get("reducer", "bounded_mean")
        if reducer_name not in REDUCERS:
            raise ValueError(f"factor {name!r} uses unknown reducer {reducer_name!r}")

        groups = factor.get("groups")
        if not isinstance(groups, list) or not groups:
            raise ValueError(f"factor {name!r} must define at least one [[factors.groups]] entry")
        signals: list[Signal] = []
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError(f"factor {name!r} groups must be tables")
            direction = float(group.get("direction", 1.0))
            if direction not in {-1.0, 1.0}:
                raise ValueError(f"factor {name!r} direction must be 1 or -1")
            signals.extend(Signal(column, direction) for column in _signal_group_columns(group, factor_name=name))
        specs.append(FactorSpec(name=name, signals=tuple(signals), reducer=REDUCERS[str(reducer_name)]))
    return tuple(specs)


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


FACTOR_SPECS = load_factor_specs()
FACTOR_COLUMNS = [spec.name for spec in FACTOR_SPECS]
OUTPUT_COLUMNS = ["available_time", *FACTOR_COLUMNS, "transition_pressure", "data_quality_score"]
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

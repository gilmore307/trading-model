"""Continuous MarketRegimeModel V1 state-vector generator.

The generator converts point-in-time rows from
``trading_data.feature_01_market_regime`` into the model output table
``trading_model.model_01_market_regime``. V1 intentionally avoids clustering,
hard state ids, supervised labels, and human-readable regime labels. The primary
output is a bounded continuous market-condition vector keyed by ``available_time``.

Factor membership, signal direction, reducer choice, and standardization
thresholds live in ``config/factor_specs.toml`` so the model contract can evolve
without editing execution code.
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
SUPPORTED_AGGREGATIONS = {"flat", "bucketed_mean"}


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
class StandardizationConfig:
    lookback: int = 120
    min_history: int = 20
    std_floor: float = 1e-8
    z_clip: float = 5.0
    min_signal_coverage: float = 0.5


@dataclass(frozen=True)
class Signal:
    column: str
    direction: float = 1.0
    bucket: str | None = None
    min_history: int | None = None
    std_floor: float | None = None
    z_clip: float | None = None


@dataclass(frozen=True)
class FactorSpec:
    name: str
    signals: tuple[Signal, ...]
    reducer: Callable[[Sequence[float]], float | None] = _bounded
    aggregation: str = "flat"
    min_signal_coverage: float | None = None


def _coerce_positive_int(value: Any, *, field: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError(f"{field} must be positive")
    return parsed


def _coerce_positive_float(value: Any, *, field: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed


def _coerce_coverage(value: Any, *, field: str) -> float:
    parsed = float(value)
    if not 0 < parsed <= 1:
        raise ValueError(f"{field} must be in (0, 1]")
    return parsed


def load_standardization_config(path: str | Path = DEFAULT_CONFIG_PATH) -> StandardizationConfig:
    config_path = Path(path)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    raw = config.get("standardization", {})
    if not isinstance(raw, dict):
        raise ValueError(f"factor config {config_path} [standardization] must be a table")
    return StandardizationConfig(
        lookback=_coerce_positive_int(raw.get("lookback", 120), field="lookback"),
        min_history=_coerce_positive_int(raw.get("min_history", 20), field="min_history"),
        std_floor=_coerce_positive_float(raw.get("std_floor", 1e-8), field="std_floor"),
        z_clip=_coerce_positive_float(raw.get("z_clip", 5.0), field="z_clip"),
        min_signal_coverage=_coerce_coverage(raw.get("min_signal_coverage", 0.5), field="min_signal_coverage"),
    )


def _signal_group_columns(group: Mapping[str, Any], *, factor_name: str) -> list[tuple[str, str | None]]:
    columns = group.get("columns")
    symbols = group.get("symbols")
    suffixes = group.get("suffixes")

    if columns and (symbols or suffixes):
        raise ValueError(f"factor {factor_name!r} group must use columns or symbols/suffixes, not both")
    if columns:
        if not isinstance(columns, list) or not all(isinstance(column, str) and column for column in columns):
            raise ValueError(f"factor {factor_name!r} columns must be a non-empty string list")
        return [(column, None) for column in columns]
    if symbols or suffixes:
        if not isinstance(symbols, list) or not all(isinstance(symbol, str) and symbol for symbol in symbols):
            raise ValueError(f"factor {factor_name!r} symbols must be a non-empty string list")
        if not isinstance(suffixes, list) or not all(isinstance(suffix, str) and suffix for suffix in suffixes):
            raise ValueError(f"factor {factor_name!r} suffixes must be a non-empty string list")
        return [(f"{symbol}_{suffix}", symbol) for symbol in symbols for suffix in suffixes]
    raise ValueError(f"factor {factor_name!r} group must define columns or symbols/suffixes")


def load_factor_specs(path: str | Path = DEFAULT_CONFIG_PATH) -> tuple[FactorSpec, ...]:
    config_path = Path(path)
    defaults = load_standardization_config(config_path)
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
        aggregation = str(factor.get("aggregation", "flat"))
        if aggregation not in SUPPORTED_AGGREGATIONS:
            raise ValueError(f"factor {name!r} uses unknown aggregation {aggregation!r}")
        min_signal_coverage = _coerce_coverage(
            factor.get("min_signal_coverage", defaults.min_signal_coverage),
            field=f"{name}.min_signal_coverage",
        )

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
            min_history = _coerce_positive_int(group.get("min_history", defaults.min_history), field=f"{name}.min_history")
            std_floor = _coerce_positive_float(group.get("std_floor", defaults.std_floor), field=f"{name}.std_floor")
            z_clip = _coerce_positive_float(group.get("z_clip", defaults.z_clip), field=f"{name}.z_clip")
            for column, bucket in _signal_group_columns(group, factor_name=name):
                signals.append(
                    Signal(
                        column=column,
                        direction=direction,
                        bucket=bucket,
                        min_history=min_history,
                        std_floor=std_floor,
                        z_clip=z_clip,
                    )
                )
        specs.append(
            FactorSpec(
                name=name,
                signals=tuple(signals),
                reducer=REDUCERS[str(reducer_name)],
                aggregation=aggregation,
                min_signal_coverage=min_signal_coverage,
            )
        )
    return tuple(specs)


class RollingZScore:
    def __init__(
        self,
        *,
        lookback: int = 120,
        min_history: int = 20,
        std_floor: float = 1e-8,
        z_clip: float = 5.0,
    ) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        if min_history < 1:
            raise ValueError("min_history must be positive")
        if std_floor <= 0:
            raise ValueError("std_floor must be positive")
        if z_clip <= 0:
            raise ValueError("z_clip must be positive")
        self.lookback = lookback
        self.min_history = min_history
        self.std_floor = std_floor
        self.z_clip = z_clip
        self.history: dict[str, list[float]] = {}

    def zscore(self, signal: Signal, value: float | None) -> float | None:
        if value is None:
            return None
        values = self.history.get(signal.column, [])[-self.lookback :]
        min_history = signal.min_history if signal.min_history is not None else self.min_history
        if len(values) < min_history:
            return None
        sigma = pstdev(values)
        std_floor = signal.std_floor if signal.std_floor is not None else self.std_floor
        if sigma < std_floor:
            return 0.0
        raw_z = (value - mean(values)) / sigma
        z_clip = signal.z_clip if signal.z_clip is not None else self.z_clip
        return max(-z_clip, min(z_clip, raw_z))

    def update(self, row: Mapping[str, Any], columns: Iterable[str]) -> None:
        for column in columns:
            value = _safe_float(row.get(column))
            if value is None:
                continue
            values = self.history.setdefault(column, [])
            values.append(value)
            if len(values) > self.lookback:
                del values[:-self.lookback]


STANDARDIZATION = load_standardization_config()
FACTOR_SPECS = load_factor_specs()
FACTOR_COLUMNS = [spec.name for spec in FACTOR_SPECS]
OUTPUT_COLUMNS = ["available_time", *FACTOR_COLUMNS, "transition_pressure", "data_quality_score"]
SPEC_BY_NAME = {spec.name: spec for spec in FACTOR_SPECS}
SIGNAL_COLUMNS = sorted({signal.column for spec in FACTOR_SPECS for signal in spec.signals})

ETF_AFFINITY_SUFFIXES = (
    "return_5d",
    "return_20d",
    "distance_to_ma20",
    "distance_to_ma50",
    "ma20_slope_5d",
    "ma_alignment_score",
)
ETF_RELATIVE_SUFFIXES = ("spy_30m",)
ETF_AFFINITY_COLUMNS = [
    "available_time",
    "etf_symbol",
    "etf_trend_score",
    "etf_relative_strength_score",
    "market_state_tailwind_score",
    "market_state_affinity_score",
    "confidence_score",
]
RISK_ON_ETFS = frozenset({
    "ARKK",
    "BITW",
    "IWM",
    "QQQ",
    "RSP",
    "SMH",
    "SPY",
    "XBI",
    "XLC",
    "XLF",
    "XLI",
    "XLK",
    "XLY",
})
DEFENSIVE_ETFS = frozenset({"GLD", "IEF", "SHY", "TLT", "UUP", "VIXY", "XLP", "XLU", "XLV"})
COMMODITY_ETFS = frozenset({"CPER", "DBA", "DBC", "GLD", "SLV", "USO", "XLE", "XLB"})
RATE_SENSITIVE_ETFS = frozenset({"ARKK", "IWM", "QQQ", "SMH", "TLT", "XLK", "XLRE", "XLY"})


def generate_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    *,
    lookback: int = STANDARDIZATION.lookback,
    min_history: int = STANDARDIZATION.min_history,
    std_floor: float = STANDARDIZATION.std_floor,
    z_clip: float = STANDARDIZATION.z_clip,
) -> list[dict[str, Any]]:
    rows = sorted(feature_rows, key=_row_available_time)
    scaler = RollingZScore(lookback=lookback, min_history=min_history, std_floor=std_floor, z_clip=z_clip)
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
    eligible_signal_columns: set[str] = set()
    total_signals = len(SIGNAL_COLUMNS)

    for spec in FACTOR_SPECS:
        factor, eligible_columns = _factor_value(spec, feature_row, scaler)
        eligible_signal_columns.update(eligible_columns)
        output[spec.name] = factor
        if factor is not None:
            factor_values[spec.name] = factor

    output["transition_pressure"] = _transition_pressure(factor_values, previous_factors)
    output["data_quality_score"] = len(eligible_signal_columns) / total_signals if total_signals else None
    return output


def _factor_value(spec: FactorSpec, row: Mapping[str, Any], scaler: RollingZScore) -> tuple[float | None, set[str]]:
    if spec.aggregation == "bucketed_mean":
        return _bucketed_factor_value(spec, row, scaler)
    adjusted: list[float] = []
    eligible_columns: set[str] = set()
    for signal in spec.signals:
        zscore = _adjusted_zscore(signal, row, scaler)
        if zscore is None:
            continue
        adjusted.append(zscore)
        eligible_columns.add(signal.column)
    if _coverage(len(adjusted), len(spec.signals)) < (spec.min_signal_coverage or 1.0):
        return None, eligible_columns
    return spec.reducer(adjusted), eligible_columns


def _bucketed_factor_value(spec: FactorSpec, row: Mapping[str, Any], scaler: RollingZScore) -> tuple[float | None, set[str]]:
    bucket_signals: dict[str, list[Signal]] = {}
    for signal in spec.signals:
        bucket_signals.setdefault(signal.bucket or signal.column, []).append(signal)

    bucket_values: list[float] = []
    eligible_columns: set[str] = set()
    for bucket, signals in bucket_signals.items():
        del bucket
        adjusted: list[float] = []
        for signal in signals:
            zscore = _adjusted_zscore(signal, row, scaler)
            if zscore is None:
                continue
            adjusted.append(zscore)
            eligible_columns.add(signal.column)
        if _coverage(len(adjusted), len(signals)) >= (spec.min_signal_coverage or 1.0):
            bucket_values.append(mean(adjusted))
    if _coverage(len(bucket_values), len(bucket_signals)) < (spec.min_signal_coverage or 1.0):
        return None, eligible_columns
    return spec.reducer(bucket_values), eligible_columns


def _adjusted_zscore(signal: Signal, row: Mapping[str, Any], scaler: RollingZScore) -> float | None:
    value = _safe_float(row.get(signal.column))
    if value is None:
        return None
    zscore = scaler.zscore(signal, value)
    if zscore is None:
        return None
    return signal.direction * zscore


def _coverage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _transition_pressure(current: Mapping[str, float], previous: Mapping[str, float] | None) -> float | None:
    if not previous:
        return None
    deltas = [abs(value - previous[name]) for name, value in current.items() if name in previous]
    if not deltas:
        return None
    return math.tanh(mean(deltas) * 2.0)


def generate_etf_affinity_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    *,
    etf_symbols: Iterable[str] | None = None,
    lookback: int = STANDARDIZATION.lookback,
    min_history: int = STANDARDIZATION.min_history,
    std_floor: float = STANDARDIZATION.std_floor,
    z_clip: float = STANDARDIZATION.z_clip,
) -> list[dict[str, Any]]:
    """Generate point-in-time ETF affinity rows for the current market state.

    The rows answer the practical Layer 1 downstream question: given the
    current market-state vector and current ETF leadership evidence, which ETFs
    are best aligned with this tape? The calculation is point-in-time: rolling
    z-scores are fit only on prior rows, and future returns remain evaluation
    labels rather than production inputs.
    """
    rows = sorted(feature_rows, key=_row_available_time)
    symbols = tuple(etf_symbols) if etf_symbols is not None else _discover_etf_symbols(rows)
    scaler = RollingZScore(lookback=lookback, min_history=min_history, std_floor=std_floor, z_clip=z_clip)
    affinity_columns = _etf_affinity_signal_columns(symbols)
    output_rows: list[dict[str, Any]] = []
    previous_factors: dict[str, float] | None = None

    for feature_row in rows:
        state_row = generate_row(feature_row, scaler=scaler, previous_factors=previous_factors)
        for symbol in symbols:
            output_rows.append(_etf_affinity_row(symbol, feature_row, state_row, scaler))
        scaler.update(feature_row, set(SIGNAL_COLUMNS).union(affinity_columns))
        previous_factors = {column: state_row[column] for column in FACTOR_COLUMNS if state_row.get(column) is not None}

    return output_rows


def _discover_etf_symbols(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    suffixes = tuple(f"_{suffix}" for suffix in ETF_AFFINITY_SUFFIXES)
    symbols: set[str] = set()
    for row in rows:
        for column in row:
            lower = str(column).lower()
            for suffix in suffixes:
                if lower.endswith(suffix):
                    symbols.add(lower[: -len(suffix)].upper())
                    break
    return tuple(sorted(symbols))


def _etf_affinity_signal_columns(symbols: Iterable[str]) -> list[str]:
    columns: set[str] = set()
    for symbol in symbols:
        lower = symbol.lower()
        columns.update(f"{lower}_{suffix}" for suffix in ETF_AFFINITY_SUFFIXES)
        if lower != "spy":
            columns.update(f"{lower}_{suffix}" for suffix in ETF_RELATIVE_SUFFIXES)
    return sorted(columns)


def _etf_affinity_row(
    symbol: str,
    feature_row: Mapping[str, Any],
    state_row: Mapping[str, Any],
    scaler: RollingZScore,
) -> dict[str, Any]:
    trend_signals = [Signal(f"{symbol.lower()}_{suffix}") for suffix in ETF_AFFINITY_SUFFIXES]
    trend_score, trend_eligible = _mean_adjusted_zscores(trend_signals, feature_row, scaler)

    relative_signals = [] if symbol.upper() == "SPY" else [Signal(f"{symbol.lower()}_{suffix}") for suffix in ETF_RELATIVE_SUFFIXES]
    relative_score, relative_eligible = _mean_adjusted_zscores(relative_signals, feature_row, scaler)

    tailwind_score = _market_state_tailwind(symbol.upper(), state_row)
    score_parts = [value for value in (trend_score, relative_score, tailwind_score) if value is not None]
    affinity_score = _bounded(score_parts) if score_parts else None

    total_signal_count = len(trend_signals) + len(relative_signals) + 1
    eligible_signal_count = trend_eligible + relative_eligible + (1 if tailwind_score is not None else 0)
    state_quality = _safe_float(state_row.get("data_quality_score"))
    raw_confidence = eligible_signal_count / total_signal_count if total_signal_count else None
    if raw_confidence is not None and state_quality is not None:
        confidence = mean([raw_confidence, state_quality])
    else:
        confidence = raw_confidence or state_quality

    return {
        "available_time": state_row["available_time"],
        "etf_symbol": symbol.upper(),
        "etf_trend_score": trend_score,
        "etf_relative_strength_score": relative_score,
        "market_state_tailwind_score": tailwind_score,
        "market_state_affinity_score": affinity_score,
        "confidence_score": confidence,
    }


def _mean_adjusted_zscores(
    signals: Sequence[Signal],
    row: Mapping[str, Any],
    scaler: RollingZScore,
) -> tuple[float | None, int]:
    adjusted = [_adjusted_zscore(signal, row, scaler) for signal in signals]
    values = [value for value in adjusted if value is not None]
    return (_bounded(values), len(values)) if values else (None, 0)


def _market_state_tailwind(symbol: str, state_row: Mapping[str, Any]) -> float | None:
    contributions: list[float] = []
    risk_appetite = _safe_float(state_row.get("risk_appetite_factor"))
    volatility_stress = _safe_float(state_row.get("volatility_stress_factor"))
    credit_stress = _safe_float(state_row.get("credit_stress_factor"))
    rate_pressure = _safe_float(state_row.get("rate_pressure_factor"))
    commodity_pressure = _safe_float(state_row.get("commodity_pressure_factor"))
    breadth = _safe_float(state_row.get("breadth_factor"))

    if risk_appetite is not None:
        if symbol in RISK_ON_ETFS:
            contributions.append(risk_appetite)
        if symbol in DEFENSIVE_ETFS:
            contributions.append(-risk_appetite)
    if volatility_stress is not None:
        if symbol in RISK_ON_ETFS:
            contributions.append(-volatility_stress)
        if symbol in DEFENSIVE_ETFS:
            contributions.append(volatility_stress)
    if credit_stress is not None:
        if symbol in RISK_ON_ETFS:
            contributions.append(-credit_stress)
        if symbol in DEFENSIVE_ETFS:
            contributions.append(credit_stress)
    if rate_pressure is not None and symbol in RATE_SENSITIVE_ETFS:
        contributions.append(-rate_pressure)
    if commodity_pressure is not None and symbol in COMMODITY_ETFS:
        contributions.append(commodity_pressure)
    if breadth is not None and symbol in {"IWM", "RSP", "SPY", "QQQ"}:
        contributions.append(breadth)

    return _bounded(contributions) if contributions else None

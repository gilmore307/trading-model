"""Continuous MarketRegimeModel V2.2 market-context state generator.

The generator converts point-in-time rows from
``trading_data.feature_01_market_regime`` into the model output table
``trading_model.model_01_market_regime``. The generator intentionally avoids
clustering, hard state ids, supervised labels, and human-readable regime labels.
The primary output is a bounded direction-neutral tradability/context vector
keyed by ``available_time``.

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
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "factor_specs.toml"
SUPPORTED_AGGREGATIONS = {"flat", "bucketed_mean"}


def _mean(values: Iterable[float]) -> float:
    if isinstance(values, Sequence):
        if not values:
            raise ValueError("mean requires at least one value")
        return sum(values) / len(values)
    items = list(values)
    if not items:
        raise ValueError("mean requires at least one value")
    return sum(items) / len(items)


def _pstdev(values: Iterable[float]) -> float:
    if not isinstance(values, Sequence):
        values = list(values)
    if len(values) < 1:
        raise ValueError("pstdev requires at least one value")
    center = sum(values) / len(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


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
    return math.tanh(_mean(values) / 2.0)


def _bounded_abs(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return math.tanh(_mean(abs(value) for value in values) / 2.0)


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
        sigma = _pstdev(values)
        std_floor = signal.std_floor if signal.std_floor is not None else self.std_floor
        if sigma < std_floor:
            return 0.0
        raw_z = (value - _mean(values)) / sigma
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
INTERNAL_SIGNAL_GROUP_COLUMNS = [spec.name for spec in FACTOR_SPECS]
STATE_OUTPUT_COLUMNS = [
    "1_market_direction_score",
    "1_market_direction_strength_score",
    "1_market_trend_quality_score",
    "1_market_stability_score",
    "1_market_risk_stress_score",
    "1_market_transition_risk_score",
    "1_breadth_participation_score",
    "1_correlation_crowding_score",
    "1_dispersion_opportunity_score",
    "1_market_liquidity_pressure_score",
    "1_market_liquidity_support_score",
    "1_coverage_score",
    "1_data_quality_score",
]
TRANSITION_BASIS_COLUMNS = [column for column in STATE_OUTPUT_COLUMNS if column not in {"1_market_transition_risk_score", "1_coverage_score", "1_data_quality_score"}]
OUTPUT_COLUMNS = ["available_time", *STATE_OUTPUT_COLUMNS]
EXPLAINABILITY_TABLE = "model_01_market_regime_explainability"
DIAGNOSTICS_TABLE = "model_01_market_regime_diagnostics"
SPEC_BY_NAME = {spec.name: spec for spec in FACTOR_SPECS}
SIGNAL_COLUMNS = sorted({signal.column for spec in FACTOR_SPECS for signal in spec.signals})
SEMANTIC_SOURCE_FACTORS = {
    "1_market_direction_score": ("1_price_behavior_factor",),
    "1_market_direction_strength_score": ("1_price_behavior_factor",),
    "1_market_trend_quality_score": ("1_trend_certainty_factor",),
    "1_market_stability_score": ("1_trend_certainty_factor", "1_risk_stress_factor"),
    "1_market_risk_stress_score": ("1_risk_stress_factor",),
    "1_market_transition_risk_score": tuple(),
    "1_breadth_participation_score": ("1_fundamental_strength_factor",),
    "1_correlation_crowding_score": ("1_market_structure_factor",),
    "1_dispersion_opportunity_score": ("1_fundamental_strength_factor", "1_market_structure_factor"),
    "1_market_liquidity_pressure_score": ("1_capital_flow_factor", "1_valuation_pressure_factor", "1_risk_stress_factor"),
    "1_market_liquidity_support_score": ("1_capital_flow_factor", "1_sentiment_factor", "1_risk_stress_factor"),
    "1_coverage_score": tuple(),
    "1_data_quality_score": tuple(),
}


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
    previous_state_values: dict[str, float] | None = None

    for feature_row in rows:
        output = generate_row(feature_row, scaler=scaler, previous_state_values=previous_state_values)
        output_rows.append(output)
        scaler.update(feature_row, SIGNAL_COLUMNS)
        previous_state_values = {column: output[column] for column in TRANSITION_BASIS_COLUMNS if output.get(column) is not None}

    return output_rows


def generate_row(
    feature_row: Mapping[str, Any],
    *,
    scaler: RollingZScore,
    previous_state_values: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {"available_time": _row_available_time(feature_row).isoformat()}
    factor_values: dict[str, float] = {}
    eligible_signal_columns: set[str] = set()
    total_signals = len(SIGNAL_COLUMNS)

    for spec in FACTOR_SPECS:
        factor, eligible_columns = _factor_value(spec, feature_row, scaler)
        eligible_signal_columns.update(eligible_columns)
        if factor is not None:
            factor_values[spec.name] = factor

    coverage = len(eligible_signal_columns) / total_signals if total_signals else None
    semantic_values = _semantic_values(factor_values, coverage_score=coverage)
    transition = _transition_pressure(
        {column: value for column, value in semantic_values.items() if column in TRANSITION_BASIS_COLUMNS and value is not None},
        previous_state_values,
    )
    semantic_values["1_market_transition_risk_score"] = transition
    output.update(semantic_values)
    return output


def _average_optional(values: Sequence[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return _mean(clean) if clean else None


def _neg(value: float | None) -> float | None:
    return None if value is None else -value


def _abs(value: float | None) -> float | None:
    return None if value is None else abs(value)


def _semantic_values(base: Mapping[str, float], *, coverage_score: float | None) -> dict[str, float | None]:
    price = _safe_float(base.get("1_price_behavior_factor"))
    trend = _safe_float(base.get("1_trend_certainty_factor"))
    capital_flow = _safe_float(base.get("1_capital_flow_factor"))
    sentiment = _safe_float(base.get("1_sentiment_factor"))
    valuation = _safe_float(base.get("1_valuation_pressure_factor"))
    breadth = _safe_float(base.get("1_fundamental_strength_factor"))
    structure = _safe_float(base.get("1_market_structure_factor"))
    risk = _safe_float(base.get("1_risk_stress_factor"))

    return {
        "1_market_direction_score": price,
        "1_market_direction_strength_score": _abs(price),
        "1_market_trend_quality_score": trend,
        "1_market_stability_score": _average_optional([trend, _neg(risk)]),
        "1_market_risk_stress_score": risk,
        "1_market_transition_risk_score": None,
        "1_breadth_participation_score": breadth,
        "1_correlation_crowding_score": structure,
        "1_dispersion_opportunity_score": _average_optional([breadth, _neg(_abs(structure))]),
        "1_market_liquidity_pressure_score": _average_optional([capital_flow, valuation, risk]),
        "1_market_liquidity_support_score": _average_optional([_neg(capital_flow), sentiment, _neg(risk)]),
        "1_coverage_score": coverage_score,
        "1_data_quality_score": coverage_score,
    }


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
            bucket_values.append(_mean(adjusted))
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
    return math.tanh(_mean(deltas) * 2.0)


def build_explainability_rows(model_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build per-factor explainability artifact rows for SQL storage.

    The rows intentionally expose reviewed factor-level context, not raw feature
    dumps. Downstream layers should depend on ``model_01_market_regime`` only;
    this artifact is for human review, attribution inspection, and model-audit
    workflows.
    """

    rows: list[dict[str, Any]] = []
    for model_row in model_rows:
        available_time = str(model_row.get("available_time") or "").strip()
        if not available_time:
            raise ValueError("model row available_time is required for explainability rows")
        for column in STATE_OUTPUT_COLUMNS:
            factor_value = _safe_float(model_row.get(column))
            source_factors = SEMANTIC_SOURCE_FACTORS.get(column, tuple())
            source_specs = [SPEC_BY_NAME[name] for name in source_factors if name in SPEC_BY_NAME]
            rows.append(
                {
                    "available_time": available_time,
                    "factor_name": column,
                    "factor_value": factor_value,
                    "explanation_payload_json": {
                        "artifact": EXPLAINABILITY_TABLE,
                        "factor_name": column,
                        "factor_value": factor_value,
                        "semantic_contract": "market_context_state",
                        "schema_version": 2,
                        "source_factor_names": list(source_factors),
                        "source_signal_count": sum(len(spec.signals) for spec in source_specs),
                        "eligible_when_factor_value_present": factor_value is not None,
                        "dependency_policy": "human_review_only_not_downstream_contract",
                    },
                }
            )
    return rows


def build_diagnostics_rows(model_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build one diagnostics artifact row per model output row."""

    rows: list[dict[str, Any]] = []
    for model_row in model_rows:
        available_time = str(model_row.get("available_time") or "").strip()
        if not available_time:
            raise ValueError("model row available_time is required for diagnostics rows")
        present_state_outputs = [column for column in STATE_OUTPUT_COLUMNS if _safe_float(model_row.get(column)) is not None]
        missing_state_outputs = [column for column in STATE_OUTPUT_COLUMNS if column not in present_state_outputs]
        data_quality_score = _safe_float(model_row.get("1_data_quality_score"))
        rows.append(
            {
                "available_time": available_time,
                "present_state_output_count": len(present_state_outputs),
                "missing_state_output_count": len(missing_state_outputs),
                "data_quality_score": data_quality_score,
                "diagnostic_payload_json": {
                    "artifact": DIAGNOSTICS_TABLE,
                    "present_state_output_columns": present_state_outputs,
                    "missing_state_output_columns": missing_state_outputs,
                    "state_output_column_count": len(STATE_OUTPUT_COLUMNS),
                    "transition_pressure": _safe_float(model_row.get("1_market_transition_risk_score")),
                    "data_quality_score": data_quality_score,
                    "acceptance_scope": "freshness_missingness_coverage_and_no_future_leak_review",
                    "dependency_policy": "gating_and_monitoring_not_downstream_prediction_contract",
                },
            }
        )
    return rows

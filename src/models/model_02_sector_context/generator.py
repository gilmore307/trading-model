"""SectorContextModel V1 deterministic state-vector generator.

This module turns point-in-time rows from
``trading_data.feature_02_sector_context`` plus optional Layer 1
``market_context_state`` rows into the three accepted Layer 2 physical artifacts:

* ``trading_model.model_02_sector_context`` (narrow downstream contract),
* ``trading_model.model_02_sector_context_explainability`` (human-review detail),
* ``trading_model.model_02_sector_context_diagnostics`` (acceptance/gating detail).

V1 is deliberately conservative: it scores reviewed sector/industry ETF behavior
without ETF holdings, stock exposure, final target selection, strategy selection,
option selection, sizing, or future-return labels.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MODEL_ID = "sector_context_model"
MODEL_VERSION = "sector_context_model_v1_contract"
PRIMARY_TABLE = "model_02_sector_context"
EXPLAINABILITY_TABLE = "model_02_sector_context_explainability"
DIAGNOSTICS_TABLE = "model_02_sector_context_diagnostics"
SUMMARY_CANDIDATE = "SECTOR_OBSERVATION_UNIVERSE"

HANDOFF_STATES = {"selected", "watch", "blocked", "insufficient_data"}
ELIGIBILITY_STATES = {"eligible", "watch", "excluded", "insufficient_data"}

IDENTITY_COLUMNS = [
    "available_time",
    "sector_or_industry_symbol",
    "model_id",
    "model_version",
    "market_context_state_ref",
]
PRIMARY_SCORE_COLUMNS = [
    "2_sector_relative_direction_score",
    "2_sector_trend_quality_score",
    "2_sector_trend_stability_score",
    "2_sector_transition_risk_score",
    "2_market_context_support_score",
    "2_sector_breadth_confirmation_score",
    "2_sector_dispersion_crowding_score",
    "2_sector_liquidity_tradability_score",
    "2_sector_tradability_score",
    "2_sector_handoff_state",
    "2_sector_handoff_bias",
    "2_sector_handoff_rank",
    "2_sector_handoff_reason_codes",
    "2_eligibility_state",
    "2_eligibility_reason_codes",
    "2_state_quality_score",
    "2_coverage_score",
    "2_data_quality_score",
    "2_evidence_count",
]
OUTPUT_COLUMNS = [*IDENTITY_COLUMNS, *PRIMARY_SCORE_COLUMNS]

EXPLAINABILITY_SCORE_COLUMNS = [
    "2_relative_strength_score",
    "2_trend_direction_score",
    "2_trend_persistence_score",
    "2_volatility_adjusted_trend_score",
    "2_breadth_participation_score",
    "2_dispersion_score",
    "2_market_correlation_score",
    "2_chop_score",
    "2_growth_sensitivity_score",
    "2_defensive_sensitivity_score",
    "2_cyclical_sensitivity_score",
    "2_rate_sensitivity_score",
    "2_dollar_sensitivity_score",
    "2_commodity_sensitivity_score",
    "2_risk_appetite_sensitivity_score",
    "2_attribute_certainty_score",
    "2_conditional_beta_score",
    "2_directional_coupling_score",
    "2_volatility_response_score",
    "2_capture_asymmetry_score",
    "2_response_convexity_score",
    "2_context_support_score",
    "2_transition_sensitivity_score",
]

DIAGNOSTIC_SCORE_COLUMNS = [
    "2_liquidity_score",
    "2_spread_cost_score",
    "2_optionability_score",
    "2_capacity_score",
    "2_tradability_score",
    "2_volatility_risk_score",
    "2_gap_risk_score",
    "2_event_density_score",
    "2_abnormal_activity_score",
    "2_correlation_stress_score",
    "2_downside_tail_risk_score",
    "2_data_quality_score",
]

FEATURE_EVIDENCE_COLUMNS = [
    "relative_strength_return",
    "relative_strength_return_30m",
    "relative_strength_return_1d",
    "relative_strength_distance_to_ma20",
    "relative_strength_distance_to_ma50",
    "relative_strength_distance_to_ma200",
    "relative_strength_slope_20d",
    "relative_strength_slope_50d",
    "relative_strength_ma20_ma50_spread",
    "relative_strength_ma50_ma200_spread",
    "relative_strength_ma_alignment_score",
    "relative_strength_realized_vol_20d_ratio",
    "relative_strength_return_corr_20d",
    "relative_strength_return_corr_60d",
    "relative_strength_return_corr_20d_60d_change",
]

SUMMARY_EVIDENCE_COLUMNS = [
    "sector_observation_positive_return_1d_pct",
    "sector_observation_positive_return_5d_pct",
    "sector_observation_above_ma20_pct",
    "sector_observation_above_ma50_pct",
    "sector_observation_above_ma200_pct",
    "sector_observation_distance_to_ma20_avg",
    "sector_observation_distance_to_ma20_dispersion",
    "sector_observation_return_20d_dispersion",
]


@dataclass(frozen=True)
class SectorGroup:
    available_time: str
    symbol: str
    feature_rows: tuple[Mapping[str, Any], ...]
    summary_row: Mapping[str, Any] | None = None
    market_context_row: Mapping[str, Any] | None = None


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


def _row_available_time(row: Mapping[str, Any]) -> str:
    return _parse_time(row.get("available_time") or row.get("snapshot_time")).isoformat()


def _bounded(value: float | None, *, scale: float = 1.0) -> float | None:
    if value is None:
        return None
    return math.tanh(value / scale)


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _magnitude(value: float | None) -> float | None:
    if value is None:
        return None
    return min(abs(value), 1.0)


def _average(values: Iterable[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return mean(clean) if clean else None


def _quality_score(present: int, total: int) -> float | None:
    if total <= 0:
        return None
    return present / total


def _evidence_count(rows: Sequence[Mapping[str, Any]]) -> int:
    return sum(1 for row in rows for column in FEATURE_EVIDENCE_COLUMNS if _safe_float(row.get(column)) is not None)


def _market_context_ref(row: Mapping[str, Any] | None, available_time: str) -> str | None:
    if row is None:
        return None
    explicit = str(row.get("market_context_state_ref") or row.get("model_run_id") or "").strip()
    if explicit:
        return explicit
    return f"model_01_market_regime:{available_time}"


def _market_context_score(row: Mapping[str, Any] | None) -> float | None:
    """Small conditioning reducer; output never copies Layer 1 factor columns."""

    if row is None:
        return None
    risk_stress = _safe_float(row.get("1_market_risk_stress_score"))
    transition_risk = _safe_float(row.get("1_market_transition_risk_score"))
    supportive = _average(
        [
            _safe_float(row.get("1_market_direction_score")),
            _safe_float(row.get("1_market_trend_quality_score")),
            _safe_float(row.get("1_market_liquidity_support_score")),
            _safe_float(row.get("1_market_stability_score")),
            -risk_stress if risk_stress is not None else None,
            -transition_risk if transition_risk is not None else None,
        ]
    )
    return supportive


def _candidate_rows(feature_rows: Iterable[Mapping[str, Any]]) -> tuple[dict[tuple[str, str], list[Mapping[str, Any]]], dict[str, Mapping[str, Any]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    summaries: dict[str, Mapping[str, Any]] = {}
    for row in feature_rows:
        available_time = _row_available_time(row)
        symbol = str(row.get("candidate_symbol") or "").strip().upper()
        if not symbol:
            continue
        if symbol == SUMMARY_CANDIDATE or row.get("candidate_type") == "sector_rotation_summary":
            summaries[available_time] = row
            continue
        grouped.setdefault((available_time, symbol), []).append(row)
    return grouped, summaries


def _market_rows_by_time(rows: Iterable[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows or []:
        result[_row_available_time(row)] = row
    return result


def _sector_groups(
    feature_rows: Iterable[Mapping[str, Any]],
    market_context_rows: Iterable[Mapping[str, Any]] | None = None,
) -> list[SectorGroup]:
    grouped, summaries = _candidate_rows(feature_rows)
    market_by_time = _market_rows_by_time(market_context_rows)
    groups: list[SectorGroup] = []
    for (available_time, symbol), rows in sorted(grouped.items()):
        groups.append(
            SectorGroup(
                available_time=available_time,
                symbol=symbol,
                feature_rows=tuple(rows),
                summary_row=summaries.get(available_time),
                market_context_row=market_by_time.get(available_time),
            )
        )
    return groups


def generate_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    market_context_rows: Iterable[Mapping[str, Any]] | None = None,
    *,
    model_version: str = MODEL_VERSION,
) -> list[dict[str, Any]]:
    """Generate primary ``model_02_sector_context`` rows."""

    provisional = [_generate_primary_row(group, model_version=model_version) for group in _sector_groups(feature_rows, market_context_rows)]
    ranked = [row for row in provisional if _safe_float(row.get("2_sector_tradability_score")) is not None and row.get("2_sector_handoff_state") in {"selected", "watch"}]
    ranked.sort(key=lambda row: (_safe_float(row.get("2_sector_tradability_score")) or -999.0), reverse=True)
    ranks = {(row["available_time"], row["sector_or_industry_symbol"]): rank for rank, row in enumerate(ranked, start=1)}
    for row in provisional:
        key = (row["available_time"], row["sector_or_industry_symbol"])
        row["2_sector_handoff_rank"] = ranks.get(key)
    return provisional


def _generate_primary_row(group: SectorGroup, *, model_version: str) -> dict[str, Any]:
    feature_rows = group.feature_rows
    evidence_count = _evidence_count(feature_rows)
    total_evidence = len(feature_rows) * len(FEATURE_EVIDENCE_COLUMNS)
    quality = _quality_score(evidence_count, total_evidence)

    rel_return_score = _bounded(_average([_safe_float(row.get("relative_strength_return")) for row in feature_rows]), scale=0.04)
    distance_score = _bounded(
        _average(
            _safe_float(row.get(column))
            for row in feature_rows
            for column in (
                "relative_strength_distance_to_ma20",
                "relative_strength_distance_to_ma50",
                "relative_strength_distance_to_ma200",
            )
        ),
        scale=0.08,
    )
    slope_score = _bounded(
        _average(_safe_float(row.get(column)) for row in feature_rows for column in ("relative_strength_slope_20d", "relative_strength_slope_50d")),
        scale=0.04,
    )
    alignment_score = _bounded(_average([_safe_float(row.get("relative_strength_ma_alignment_score")) for row in feature_rows]), scale=1.0)
    sector_direction = _average([rel_return_score, distance_score, slope_score, alignment_score])

    vol_penalty = _average([abs((_safe_float(row.get("relative_strength_realized_vol_20d_ratio")) or 1.0) - 1.0) for row in feature_rows if _safe_float(row.get("relative_strength_realized_vol_20d_ratio")) is not None])
    volatility_adjustment = None if vol_penalty is None else max(0.0, 1.0 - min(vol_penalty, 1.0))
    corr_change = _average([_safe_float(row.get("relative_strength_return_corr_20d_60d_change")) for row in feature_rows])
    transition_risk = _clip01(_average([_magnitude(corr_change), None if volatility_adjustment is None else 1.0 - volatility_adjustment]))

    trend_quality = _clip01(_average([_magnitude(rel_return_score), _magnitude(distance_score), _magnitude(slope_score), _magnitude(alignment_score), volatility_adjustment]))
    trend_stability = _clip01(_average([_magnitude(alignment_score), volatility_adjustment, None if transition_risk is None else 1.0 - transition_risk]))

    market_context = _bounded(_market_context_score(group.market_context_row), scale=1.0)
    market_context_support = None if sector_direction is None or market_context is None else sector_direction * market_context

    summary = group.summary_row or {}
    breadth = _clip01(_average([_safe_float(summary.get(column)) for column in ("sector_observation_positive_return_1d_pct", "sector_observation_positive_return_5d_pct", "sector_observation_above_ma20_pct", "sector_observation_above_ma50_pct")]))
    dispersion_raw = _average([_safe_float(summary.get("sector_observation_distance_to_ma20_dispersion")), _safe_float(summary.get("sector_observation_return_20d_dispersion"))])
    dispersion_crowding = _clip01(None if dispersion_raw is None else dispersion_raw / 0.10)
    liquidity_tradability = None
    coverage = quality
    data_quality = quality
    state_quality = _clip01(_average([coverage, data_quality, None if transition_risk is None else 1.0 - transition_risk]))
    sector_tradability = _clip01(
        _average(
            [
                trend_quality,
                trend_stability,
                None if transition_risk is None else 1.0 - transition_risk,
                breadth,
                None if dispersion_crowding is None else 1.0 - dispersion_crowding,
                liquidity_tradability,
                state_quality,
            ]
        )
    )

    handoff_bias = _handoff_bias(sector_direction)
    handoff_state, eligibility_state, reason_codes = _states(sector_tradability, quality, transition_risk, evidence_count, handoff_bias)
    return {
        "available_time": group.available_time,
        "sector_or_industry_symbol": group.symbol,
        "model_id": MODEL_ID,
        "model_version": model_version,
        "market_context_state_ref": _market_context_ref(group.market_context_row, group.available_time),
        "2_sector_relative_direction_score": sector_direction,
        "2_sector_trend_quality_score": trend_quality,
        "2_sector_trend_stability_score": trend_stability,
        "2_sector_transition_risk_score": transition_risk,
        "2_market_context_support_score": market_context_support,
        "2_sector_breadth_confirmation_score": breadth,
        "2_sector_dispersion_crowding_score": dispersion_crowding,
        "2_sector_liquidity_tradability_score": liquidity_tradability,
        "2_sector_tradability_score": sector_tradability,
        "2_sector_handoff_state": handoff_state,
        "2_sector_handoff_bias": handoff_bias,
        "2_sector_handoff_rank": None,
        "2_sector_handoff_reason_codes": ";".join(reason_codes),
        "2_eligibility_state": eligibility_state,
        "2_eligibility_reason_codes": ";".join(reason_codes),
        "2_state_quality_score": state_quality,
        "2_coverage_score": coverage,
        "2_data_quality_score": data_quality,
        "2_evidence_count": evidence_count,
    }


def _handoff_bias(sector_direction: float | None) -> str:
    if sector_direction is None:
        return "mixed"
    if sector_direction >= 0.15:
        return "long_bias"
    if sector_direction <= -0.15:
        return "short_bias"
    return "neutral"


def _states(tradability: float | None, quality: float | None, transition_risk: float | None, evidence_count: int, handoff_bias: str) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    if evidence_count <= 0 or tradability is None or quality is None:
        return "insufficient_data", "insufficient_data", ["2_INSUFFICIENT_POINT_IN_TIME_EVIDENCE"]
    if quality < 0.25:
        reasons.append("2_LOW_EVIDENCE_COVERAGE")
        return "insufficient_data", "insufficient_data", reasons
    if transition_risk is not None and transition_risk >= 0.75:
        reasons.append("2_HIGH_TRANSITION_RISK")
        return "blocked", "excluded", reasons
    bias_reason = {
        "long_bias": "2_LONG_BIAS",
        "short_bias": "2_SHORT_BIAS",
        "neutral": "2_NEUTRAL_BIAS",
        "mixed": "2_MIXED_BIAS",
    }.get(handoff_bias, "2_MIXED_BIAS")
    if tradability >= 0.55:
        return "selected", "eligible", ["2_DIRECTION_NEUTRAL_TRADABILITY_SELECTED", bias_reason]
    if tradability >= 0.35:
        return "watch", "watch", ["2_DIRECTION_NEUTRAL_TRADABILITY_WATCH", bias_reason]
    reasons.append("2_DIRECTION_NEUTRAL_TRADABILITY_BLOCKED")
    reasons.append(bias_reason)
    return "blocked", "excluded", reasons


def build_explainability_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    market_context_rows: Iterable[Mapping[str, Any]] | None = None,
    *,
    model_version: str = MODEL_VERSION,
) -> list[dict[str, Any]]:
    """Build support rows for human review and attribution inspection."""

    del model_version
    rows: list[dict[str, Any]] = []
    for group in _sector_groups(feature_rows, market_context_rows):
        rel_returns = [_safe_float(row.get("relative_strength_return")) for row in group.feature_rows]
        trend_direction = _bounded(_average(rel_returns), scale=0.04)
        trend_persistence = _bounded(_average([_safe_float(row.get("relative_strength_ma_alignment_score")) for row in group.feature_rows]), scale=1.0)
        vol_ratio = _average([_safe_float(row.get("relative_strength_realized_vol_20d_ratio")) for row in group.feature_rows])
        vol_adjusted = None if trend_direction is None else trend_direction / max(vol_ratio or 1.0, 0.01)
        corr = _average([_safe_float(row.get("relative_strength_return_corr_20d")) for row in group.feature_rows])
        corr_change = _average([_safe_float(row.get("relative_strength_return_corr_20d_60d_change")) for row in group.feature_rows])
        summary = group.summary_row or {}
        breadth = _average([_safe_float(summary.get(column)) for column in ("sector_observation_positive_return_1d_pct", "sector_observation_positive_return_5d_pct", "sector_observation_above_ma20_pct")])
        dispersion = _average([_safe_float(summary.get("sector_observation_distance_to_ma20_dispersion")), _safe_float(summary.get("sector_observation_return_20d_dispersion"))])
        context_support = _bounded(_market_context_score(group.market_context_row), scale=1.0)
        values = {
            "2_relative_strength_score": _bounded(_average(rel_returns), scale=0.04),
            "2_trend_direction_score": trend_direction,
            "2_trend_persistence_score": trend_persistence,
            "2_volatility_adjusted_trend_score": vol_adjusted,
            "2_breadth_participation_score": breadth,
            "2_dispersion_score": dispersion,
            "2_market_correlation_score": corr,
            "2_chop_score": None if corr is None else 1.0 - abs(corr),
            "2_growth_sensitivity_score": _average([trend_direction, corr]),
            "2_defensive_sensitivity_score": None if trend_direction is None else -trend_direction,
            "2_cyclical_sensitivity_score": _average([trend_direction, breadth]),
            "2_rate_sensitivity_score": None,
            "2_dollar_sensitivity_score": None,
            "2_commodity_sensitivity_score": None,
            "2_risk_appetite_sensitivity_score": _average([trend_direction, context_support]),
            "2_attribute_certainty_score": _quality_score(_evidence_count(group.feature_rows), len(group.feature_rows) * len(FEATURE_EVIDENCE_COLUMNS)),
            "2_conditional_beta_score": corr,
            "2_directional_coupling_score": corr,
            "2_volatility_response_score": None if vol_ratio is None else vol_ratio - 1.0,
            "2_capture_asymmetry_score": trend_direction,
            "2_response_convexity_score": None,
            "2_context_support_score": context_support,
            "2_transition_sensitivity_score": corr_change,
        }
        rows.append(
            {
                "available_time": group.available_time,
                "sector_or_industry_symbol": group.symbol,
                **values,
                "explanation_payload_json": {
                    "artifact": EXPLAINABILITY_TABLE,
                    "dependency_policy": "human_review_only_not_downstream_contract",
                    "source_feature_row_count": len(group.feature_rows),
                    "rotation_pair_ids": sorted(str(row.get("rotation_pair_id")) for row in group.feature_rows),
                    "uses_layer1_as_conditioning_context": group.market_context_row is not None,
                    "excludes_etf_holdings_and_stock_exposure": True,
                },
            }
        )
    return rows


def build_diagnostics_rows(
    feature_rows: Iterable[Mapping[str, Any]],
    market_context_rows: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build support rows for acceptance, monitoring, and gating."""

    rows: list[dict[str, Any]] = []
    for group in _sector_groups(feature_rows, market_context_rows):
        evidence_count = _evidence_count(group.feature_rows)
        total_evidence = len(group.feature_rows) * len(FEATURE_EVIDENCE_COLUMNS)
        quality = _quality_score(evidence_count, total_evidence)
        vol_ratio = _average([_safe_float(row.get("relative_strength_realized_vol_20d_ratio")) for row in group.feature_rows])
        corr = _average([_safe_float(row.get("relative_strength_return_corr_20d")) for row in group.feature_rows])
        corr_change = _average([_safe_float(row.get("relative_strength_return_corr_20d_60d_change")) for row in group.feature_rows])
        rows.append(
            {
                "available_time": group.available_time,
                "sector_or_industry_symbol": group.symbol,
                "2_liquidity_score": None,
                "2_spread_cost_score": None,
                "2_optionability_score": None,
                "2_capacity_score": None,
                "2_tradability_score": None,
                "2_volatility_risk_score": None if vol_ratio is None else min(abs(vol_ratio - 1.0), 1.0),
                "2_gap_risk_score": None,
                "2_event_density_score": None,
                "2_abnormal_activity_score": None,
                "2_correlation_stress_score": None if corr is None else abs(corr),
                "2_downside_tail_risk_score": None,
                "2_data_quality_score": quality,
                "diagnostic_payload_json": {
                    "artifact": DIAGNOSTICS_TABLE,
                    "dependency_policy": "gating_and_monitoring_not_downstream_prediction_contract",
                    "feature_evidence_count": evidence_count,
                    "feature_evidence_total": total_evidence,
                    "source_feature_row_count": len(group.feature_rows),
                    "has_market_context_state": group.market_context_row is not None,
                    "correlation_change": corr_change,
                    "no_future_leak_policy": "point_in_time_inputs_only_no_future_returns_or_realized_pnl",
                    "excluded_inputs": ["etf_holdings", "stock_etf_exposure", "final_target_symbols", "strategy_choice", "option_contracts"],
                },
            }
        )
    return rows

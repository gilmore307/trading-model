"""Historical evaluation pass for the current six-model chain.

This module builds current M01-M06 rows from existing point-in-time historical
feature rows. It is model-side evidence only: it reads historical data,
builds chronological folds, may train a local baseline utility artifact, and
never promotes, activates, writes broker/account state, or mutates SQL.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from model_governance.current_chain import build_current_chain_rows
from model_governance.training import LightGBMScoreModelSpec, predict_lightgbm_score, train_lightgbm_score_model

ET = ZoneInfo("America/New_York")
CURRENT_MODEL_HISTORICAL_SCHEMA = "current_model_historical_evaluation_artifact"
TARGET_STATE_SOURCE_TABLE = "model_03_target_state_vector_data_acquisition"
TARGET_STATE_FEATURE_TABLE = "model_03_target_state_vector_feature_generation"
HORIZONS = ("10min", "1h", "1D", "1W")
BASELINE_FEATURE_NAMES = (
    "m01_market_risk_stress_1w",
    "m01_liquidity_support_1w",
    "m02_target_direction_1w",
    "m02_tradability_1w",
    "m03_event_path_risk_1w",
    "m04_after_cost_edge_1w",
    "m04_materiality_adjusted_action_1w",
    "m05_expression_confidence_1w",
    "m06_intervention_severity",
)


@dataclass(frozen=True)
class HistoricalInputRow:
    """Point-in-time historical row plus mature future label."""

    source_row: Mapping[str, Any]
    payload: Mapping[str, Any]
    label_payload: Mapping[str, Any]


def load_historical_rows_from_database(
    cursor: Any,
    *,
    start_time: str,
    end_time: str,
    limit: int,
    per_month_limit: int = 250,
    label_horizon_days: int = 7,
    schema_data: str = "trading_data",
) -> list[HistoricalInputRow]:
    """Read bounded historical rows from existing point-in-time feature tables."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    cursor.execute(
        f"""
        WITH ranked_candidates AS (
          SELECT
            fg.available_time,
            fg.tradeable_time,
            fg.target_candidate_id,
            fg.market_state_features,
            fg.sector_state_features,
            fg.target_state_features,
            fg.cross_state_features,
            fg.feature_quality_diagnostics,
            da.symbol,
            da.bar_close,
            da.dollar_volume,
            da.avg_bid,
            da.avg_ask,
            da.spread_bps,
            date_trunc('day', fg.available_time) AS sample_day,
            row_number() OVER (
              PARTITION BY fg.available_time
              ORDER BY
                COALESCE(da.dollar_volume, 0) DESC,
                COALESCE(da.spread_bps, 1000000) ASC,
                fg.target_candidate_id ASC
            ) AS point_in_time_candidate_rank
          FROM "{schema_data}"."{TARGET_STATE_FEATURE_TABLE}" fg
          JOIN "{schema_data}"."{TARGET_STATE_SOURCE_TABLE}" da
            ON da.target_candidate_id = fg.target_candidate_id
           AND da.available_time = fg.available_time
          WHERE fg.available_time >= %s::timestamptz
            AND fg.available_time < %s::timestamptz
            AND da.bar_close IS NOT NULL
        ),
        daily_stratified AS (
          SELECT
            ranked_candidates.*,
            row_number() OVER (
              PARTITION BY date_trunc('month', available_time), sample_day
              ORDER BY point_in_time_candidate_rank, available_time, target_candidate_id
            ) AS daily_sample_rank
          FROM ranked_candidates
        ),
        monthly_sample AS (
          SELECT
            daily_stratified.*,
            row_number() OVER (
              PARTITION BY date_trunc('month', available_time)
              ORDER BY daily_sample_rank, sample_day, available_time, point_in_time_candidate_rank, target_candidate_id
            ) AS month_row_number
          FROM daily_stratified
        )
        SELECT
          monthly_sample.available_time,
          monthly_sample.tradeable_time,
          monthly_sample.target_candidate_id,
          monthly_sample.market_state_features,
          monthly_sample.sector_state_features,
          monthly_sample.target_state_features,
          monthly_sample.cross_state_features,
          monthly_sample.feature_quality_diagnostics,
          monthly_sample.symbol,
          monthly_sample.bar_close,
          monthly_sample.dollar_volume,
          monthly_sample.avg_bid,
          monthly_sample.avg_ask,
          monthly_sample.spread_bps,
          monthly_sample.point_in_time_candidate_rank,
          monthly_sample.daily_sample_rank,
          future_bar.available_time AS label_time,
          future_bar.bar_close AS future_close
        FROM monthly_sample
        LEFT JOIN LATERAL (
          SELECT available_time, bar_close
          FROM "{schema_data}"."{TARGET_STATE_SOURCE_TABLE}" future_da
          WHERE future_da.target_candidate_id = monthly_sample.target_candidate_id
            AND future_da.available_time >= monthly_sample.tradeable_time + (%s::text || ' days')::interval
            AND future_da.bar_close IS NOT NULL
          ORDER BY future_da.available_time
          LIMIT 1
        ) future_bar ON TRUE
        WHERE monthly_sample.month_row_number <= %s
        ORDER BY monthly_sample.available_time, monthly_sample.point_in_time_candidate_rank, monthly_sample.target_candidate_id
        LIMIT %s
        """,
        (start_time, end_time, label_horizon_days, per_month_limit, limit),
    )
    rows = []
    for row in cursor.fetchall():
        source = dict(row)
        payload = historical_source_row_to_payload(source)
        label = _label_payload(source)
        rows.append(HistoricalInputRow(source_row=source, payload=payload, label_payload=label))
    return rows


def historical_source_row_to_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map one historical source row into the current-chain payload."""

    available_time = _iso(_parse_time(row.get("available_time")))
    tradeable_time = _iso(_parse_time(row.get("tradeable_time") or available_time))
    market = _mapping(row.get("market_state_features"))
    sector = _mapping(row.get("sector_state_features"))
    target = _mapping(row.get("target_state_features"))
    quality = _mapping(row.get("feature_quality_diagnostics"))
    market_payload = _mapping(market.get("market_context_payload"))
    sector_payload = _mapping(sector.get("sector_context_payload"))
    target_price = _mapping(target.get("target_price_state"))
    target_quality = _mapping(target.get("target_data_quality_state"))
    symbol = str(row.get("symbol") or "UNKNOWN").upper()
    bar_close = _float(row.get("bar_close"), 0.0)
    spread_bps = _float(row.get("spread_bps"), 10.0)
    bid = _float(row.get("avg_bid"), bar_close)
    ask = _float(row.get("avg_ask"), bar_close)
    if bid <= 0 and bar_close > 0:
        bid = bar_close * 0.9995
    if ask <= 0 and bar_close > 0:
        ask = bar_close * 1.0005
    dollar_volume = _float(row.get("dollar_volume"), 0.0)

    return {
        "background_input": _background_input(available_time, market, market_payload, sector_payload, quality),
        "target_candidate_id": str(row.get("target_candidate_id") or ""),
        "routing_symbol": symbol,
        "sector_type": str(sector_payload.get("sector_or_industry_symbol") or "unknown").lower(),
        "tradeable_time": tradeable_time,
        "anonymous_target_feature_vector": _target_feature_vector(target, target_price, target_quality),
        "accepted_event_contracts": [],
        "quality_calibration_state": {
            "data_quality_score": _clip01(_float(quality.get("history_bars"), 1.0) / 120.0),
            "walk_forward_reliability_score": 0.55,
            "out_of_distribution_score": 0.20 if _float(quality.get("history_bars"), 0.0) < 30 else 0.10,
        },
        "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.80, "correlation_concentration_score": 0.20},
        "account_capacity_state": {"cash_capacity_score": 0.80, "drawdown_pressure_score": 0.15},
        "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
        "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
        "cost_friction_state": {
            "spread_cost_estimate": max(spread_bps, 0.0) / 10000.0,
            "slippage_cost_estimate": 0.001,
            "fee_cost_estimate": 0.0005,
            "turnover_cost_estimate": 0.001,
        },
        "underlying_quote_state": {
            "reference_price": bar_close,
            "bid_price": bid,
            "ask_price": ask,
            "halt_status": "active",
        },
        "underlying_liquidity_state": {
            "spread_bps": spread_bps,
            "dollar_volume": dollar_volume,
            "liquidity_score": _clip01(dollar_volume / 50_000_000.0) if dollar_volume else 0.25,
        },
        "underlying_borrow_state": {"short_borrow_status": "available"},
        "risk_budget_state": {"risk_budget_available_score": 0.80},
        "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
        "option_expression_policy": {
            "option_expression_allowed": False,
            "allow_underlying_only_expression": True,
            "option_surface_status": "optionable_chain_missing",
        },
        "option_contract_candidates": [],
        "event_observations": [],
    }


def run_historical_current_chain_evaluation(
    rows: Sequence[HistoricalInputRow],
    *,
    run_id: str | None = None,
    train_baseline: bool = True,
) -> dict[str, Any]:
    """Run current-chain rows, fold metrics, and optional learned baseline artifact."""

    normalized_run_id = run_id or _stable_id("current_model_historical_eval", len(rows), _iso(datetime.now(tz=ET)))
    examples = []
    blocked_rows = []
    for index, historical_row in enumerate(rows):
        try:
            chain_rows = build_current_chain_rows(historical_row.payload, use_fixture_defaults=False)
        except Exception as exc:  # pragma: no cover - defensive evidence path
            blocked_rows.append({"row_index": index, "target_candidate_id": historical_row.payload.get("target_candidate_id"), "error": str(exc)})
            continue
        examples.append(_example_from_chain(historical_row, chain_rows))

    folds = _folds(examples)
    baseline = _baseline_training_artifact(examples, folds) if train_baseline else _skipped_baseline("baseline_training_disabled")
    metrics = _fold_metrics(examples, folds, baseline.get("artifact"))
    label_count = sum(1 for example in examples if example["label_payload"]["label_matured"])
    target_candidate_count = len({str(example["target_candidate_id"]) for example in examples})
    routing_symbol_count = len({str(example["routing_symbol"]) for example in examples})
    blocked_reasons = []
    if not rows:
        blocked_reasons.append("no_historical_rows")
    if blocked_rows:
        blocked_reasons.append("current_chain_row_generation_failed")
    if label_count == 0:
        blocked_reasons.append("no_matured_labels")
    if baseline.get("training_status") != "trained":
        blocked_reasons.append("baseline_training_not_completed")
    if len(examples) > 1 and target_candidate_count < 2:
        blocked_reasons.append("insufficient_target_candidate_diversity")
    if len(examples) > 1 and routing_symbol_count < 2:
        blocked_reasons.append("insufficient_routing_symbol_diversity")
    warning_reasons = _warning_reasons(examples)

    receipt = {
        "contract_type": "current_model_historical_evaluation_receipt",
        "schema_version": CURRENT_MODEL_HISTORICAL_SCHEMA,
        "run_id": normalized_run_id,
        "source_selection_policy": "point_in_time_liquidity_ranked_daily_stratified_sample",
        "row_count": len(rows),
        "generated_chain_row_count": len(examples),
        "blocked_source_row_count": len(blocked_rows),
        "unique_target_candidate_count": target_candidate_count,
        "unique_routing_symbol_count": routing_symbol_count,
        "label_row_count": label_count,
        "label_join_coverage_rate": round(label_count / len(examples), 6) if examples else 0.0,
        "fold_count": len(folds),
        "folds": folds,
        "baseline_training_status": baseline.get("training_status"),
        "model_training_performed": baseline.get("training_status") == "trained",
        "evaluation_status": "passed" if not blocked_reasons else "blocked",
        "blocking_reasons": blocked_reasons,
        "warning_reasons": warning_reasons,
        "activation_allowed": False,
        "production_promotion_allowed": False,
        "provider_calls_performed": False,
        "sql_mutation_performed": False,
        "broker_or_account_mutation_performed": False,
    }
    return {
        "receipt": receipt,
        "source_row_errors": blocked_rows,
        "baseline": baseline,
        "fold_metrics": metrics,
        "tables": _artifact_tables(normalized_run_id, examples, folds, metrics, receipt),
        "sample_examples": examples[:5],
    }


def _background_input(
    available_time: str,
    market: Mapping[str, Any],
    market_payload: Mapping[str, Any],
    sector_payload: Mapping[str, Any],
    quality: Mapping[str, Any],
) -> dict[str, Any]:
    multi = _mapping(market.get("multi_frame_state"))
    output = {"available_time": available_time}
    for horizon in HORIZONS:
        frame = _mapping(multi.get(horizon))
        output[f"market_return_{horizon}"] = _signed(frame.get("return"), _signed(market_payload.get("1_market_direction_score"), 0.0))
        output[f"market_trend_quality_score_{horizon}"] = abs(_signed(frame.get("trend_quality"), _signed(market_payload.get("1_market_trend_quality_score"), 0.55)))
        output[f"market_volatility_pressure_score_{horizon}"] = _clip01(_float(frame.get("volatility"), abs(_float(market_payload.get("1_market_risk_stress_score"), 0.25))))
        output[f"market_liquidity_support_score_{horizon}"] = _clip01(_float(frame.get("liquidity_tradability"), 0.5 + 0.5 * _signed(market_payload.get("1_market_liquidity_support_score"), 0.4)))
        output[f"sector_relative_direction_score_{horizon}"] = _signed(sector_payload.get("2_sector_relative_direction_score"), 0.0)
        output[f"sector_breadth_score_{horizon}"] = _clip01(_float(sector_payload.get("2_sector_breadth_confirmation_score"), 0.5))
        output[f"sector_dispersion_score_{horizon}"] = _clip01(_float(sector_payload.get("2_sector_internal_dispersion_score"), 0.25))
    output["data_quality_score"] = _clip01(_float(market_payload.get("1_data_quality_score"), 0.5))
    output["coverage_score"] = _clip01(_float(market_payload.get("1_coverage_score"), 0.5))
    output["market_context_features"] = dict(market)
    output["sector_context_features"] = {"sector_context_payload": dict(sector_payload), "feature_quality_diagnostics": dict(quality)}
    return output


def _target_feature_vector(
    target: Mapping[str, Any],
    target_price: Mapping[str, Any],
    target_quality: Mapping[str, Any],
) -> dict[str, Any]:
    multi = _mapping(target.get("multi_frame_state"))
    output: dict[str, Any] = {
        "target_liquidity_tradability_score": 1.0 if target_quality.get("has_volume") else 0.35,
        "target_volatility_pressure_score": 0.25,
        "target_transition_risk_score": 0.20,
        "reference_price": _float(target_price.get("bar_close"), 0.0),
    }
    for horizon in HORIZONS:
        frame = _mapping(multi.get(horizon))
        output[f"target_return_{horizon}"] = _signed(frame.get("return"), 0.0)
        output[f"target_trend_quality_score_{horizon}"] = abs(_signed(frame.get("trend_quality"), 0.55))
        output[f"target_volatility_pressure_score_{horizon}"] = _clip01(_float(frame.get("realized_vol"), 0.25))
        output[f"target_transition_risk_score_{horizon}"] = _clip01(_float(frame.get("late_trend_risk_score"), 0.20))
    return output


def _label_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    close = _float(row.get("bar_close"), 0.0)
    future_close = _float(row.get("future_close"), 0.0)
    label_matured = close > 0 and future_close > 0 and row.get("label_time") is not None
    future_return = (future_close - close) / close if label_matured else None
    return {
        "label_name": "future_target_return_1W",
        "horizon": "1W",
        "available_time": _iso(_parse_time(row.get("available_time"))),
        "label_time": _iso(_parse_time(row.get("label_time"))) if row.get("label_time") else None,
        "label_matured": label_matured,
        "current_close": close,
        "future_close": future_close if label_matured else None,
        "future_return_1W": future_return,
        "utility_score_1W": _clip01(0.5 + float(future_return or 0.0) * 5.0) if label_matured else None,
    }


def _example_from_chain(historical_row: HistoricalInputRow, rows: Mapping[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_surface = {surface: surface_rows[0] for surface, surface_rows in rows.items() if surface_rows}
    decision = by_surface["model_04_unified_decision"]
    option = by_surface["model_05_option_expression"]
    residual = by_surface["model_06_residual_event_governance"]
    label = dict(historical_row.label_payload)
    return {
        "available_time": historical_row.payload["background_input"]["available_time"],
        "target_candidate_id": historical_row.payload["target_candidate_id"],
        "routing_symbol": historical_row.payload["routing_symbol"],
        "fold_key": _month_key(historical_row.payload["background_input"]["available_time"]),
        "label_payload": label,
        "feature_vector": _baseline_features(by_surface),
        "resolved_outputs": {
            "background_context_state_ref": by_surface["model_01_background_context"]["background_context_state_ref"],
            "target_context_state_ref": by_surface["model_02_target_state"]["target_context_state_ref"],
            "event_state_vector_ref": by_surface["model_03_event_state"]["event_state_vector_ref"],
            "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
            "option_expression_plan_ref": option["option_expression_plan_ref"],
            "event_risk_intervention_ref": residual["event_risk_intervention_ref"],
            "resolved_underlying_action": decision["4_resolved_underlying_action_type"],
            "resolved_option_expression": option["5_resolved_expression_type"],
            "resolved_event_intervention": residual["6_resolved_intervention_action"],
        },
    }


def _baseline_features(rows: Mapping[str, Mapping[str, Any]]) -> list[float]:
    background = rows["model_01_background_context"]
    target = rows["model_02_target_state"]
    event = rows["model_03_event_state"]
    decision = rows["model_04_unified_decision"]
    option = rows["model_05_option_expression"]
    residual = rows["model_06_residual_event_governance"]
    return [
        _float(background.get("1_market_risk_stress_score_1W"), 0.0),
        _float(background.get("1_market_liquidity_support_score_1W"), 0.0),
        _signed(target.get("2_target_direction_score_1W"), 0.0),
        _float(target.get("2_tradability_score_1W"), 0.0),
        _float(event.get("3_event_path_risk_score_1W"), 0.0),
        _float(decision.get("4_after_cost_edge_score_1W"), 0.0),
        _float(decision.get("4_materiality_adjusted_action_score_1W"), 0.0),
        _float(option.get("5_option_expression_confidence_score_1W"), 0.0),
        _float(residual.get("6_resolved_intervention_severity_score"), 0.0),
    ]


def _folds(examples: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    keys = sorted({str(example["fold_key"]) for example in examples})
    return [
        {
            "split_id": f"fold_{key}",
            "split_name": "train" if index == 0 else ("validation" if index == 1 else "test"),
            "fold_key": key,
            "split_order": index,
            "row_count": sum(1 for example in examples if example["fold_key"] == key),
        }
        for index, key in enumerate(keys)
    ]


def _baseline_training_artifact(examples: Sequence[Mapping[str, Any]], folds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(folds) < 2:
        return _skipped_baseline("requires_at_least_two_chronological_folds")
    first_eval_order = 1
    train_fold_keys = {fold["fold_key"] for fold in folds if int(fold["split_order"]) < first_eval_order}
    train_examples = [
        example
        for example in examples
        if example["fold_key"] in train_fold_keys and example["label_payload"].get("utility_score_1W") is not None
    ]
    if len(train_examples) < 2:
        return _skipped_baseline("requires_at_least_two_labeled_training_rows")
    spec = LightGBMScoreModelSpec(
        schema_version="current_chain_utility_baseline_artifact",
        model_id="current_chain_utility_baseline",
        model_version="historical_evaluation_baseline",
        model_type="lightgbm_gbdt_current_chain_utility_score",
        score_semantics="0.5_neutral_future_1w_utility",
        seed=11,
        iterations=50,
        learning_rate=0.08,
    )
    artifact = train_lightgbm_score_model(
        spec=spec,
        feature_rows=[example["feature_vector"] for example in train_examples],
        targets=[float(example["label_payload"]["utility_score_1W"]) for example in train_examples],
        feature_names=BASELINE_FEATURE_NAMES,
        artifact_fields={
            "training_fold_keys": sorted(train_fold_keys),
            "production_promotion_allowed": False,
            "activation_allowed": False,
        },
    )
    return {"training_status": "trained", "artifact": artifact}


def _skipped_baseline(reason: str) -> dict[str, Any]:
    return {
        "training_status": "skipped",
        "reason_codes": [reason],
        "artifact": None,
    }


def _fold_metrics(
    examples: Sequence[Mapping[str, Any]],
    folds: Sequence[Mapping[str, Any]],
    artifact: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    metrics = []
    for fold in folds:
        fold_examples = [example for example in examples if example["fold_key"] == fold["fold_key"]]
        labeled = [example for example in fold_examples if example["label_payload"].get("utility_score_1W") is not None]
        predictions = [predict_lightgbm_score(example["feature_vector"], artifact) for example in labeled] if artifact else []
        targets = [float(example["label_payload"]["utility_score_1W"]) for example in labeled]
        mae = (
            sum(abs(prediction - target) for prediction, target in zip(predictions, targets)) / len(targets)
            if predictions and targets
            else None
        )
        metrics.append(
            {
                "split_id": fold["split_id"],
                "split_name": fold["split_name"],
                "fold_key": fold["fold_key"],
                "row_count": len(fold_examples),
                "label_count": len(labeled),
                "label_coverage_rate": round(len(labeled) / len(fold_examples), 6) if fold_examples else 0.0,
                "mean_future_return_1W": _mean([example["label_payload"]["future_return_1W"] for example in labeled]),
                "baseline_prediction_mae": round(mae, 8) if mae is not None else None,
                "resolved_underlying_action_counts": dict(Counter(example["resolved_outputs"]["resolved_underlying_action"] for example in fold_examples)),
                "resolved_option_expression_counts": dict(Counter(example["resolved_outputs"]["resolved_option_expression"] for example in fold_examples)),
                "resolved_event_intervention_counts": dict(Counter(example["resolved_outputs"]["resolved_event_intervention"] for example in fold_examples)),
            }
        )
    return metrics


def _warning_reasons(examples: Sequence[Mapping[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not examples:
        return warnings
    target_count = len({str(example["target_candidate_id"]) for example in examples})
    symbol_count = len({str(example["routing_symbol"]) for example in examples})
    action_counts = Counter(example["resolved_outputs"]["resolved_underlying_action"] for example in examples)
    option_counts = Counter(example["resolved_outputs"]["resolved_option_expression"] for example in examples)
    intervention_counts = Counter(example["resolved_outputs"]["resolved_event_intervention"] for example in examples)
    if target_count == 1 and len(examples) > 1:
        warnings.append("low_target_candidate_diversity")
    if symbol_count == 1 and len(examples) > 1:
        warnings.append("low_routing_symbol_diversity")
    if len(action_counts) == 1:
        warnings.append("degenerate_underlying_action_distribution")
    if len(option_counts) == 1:
        warnings.append("degenerate_option_expression_distribution")
    if len(intervention_counts) == 1:
        warnings.append("degenerate_event_intervention_distribution")
    return warnings


def _artifact_tables(
    run_id: str,
    examples: Sequence[Mapping[str, Any]],
    folds: Sequence[Mapping[str, Any]],
    metrics: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    if examples:
        start = min(str(example["available_time"]) for example in examples)
        end = max(str(example["available_time"]) for example in examples)
    else:
        start = end = _iso(datetime.now(tz=ET))
    snapshot_id = f"snapshot_{run_id}"
    eval_run_id = f"eval_{run_id}"
    return {
        "model_dataset_request": [
            {
                "request_id": f"request_{run_id}",
                "model_id": "current_six_model_chain",
                "purpose": "historical_current_chain_evaluation",
                "required_data_start_time": start,
                "required_data_end_time": end,
                "required_source_key": f"trading_data.{TARGET_STATE_FEATURE_TABLE}",
                "required_feature_key": "migration_source_current_chain_payload",
                "request_status": "completed" if receipt.get("evaluation_status") == "passed" else "blocked",
                "request_payload_json": {"receipt": dict(receipt)},
                "completed_at": end,
                "status_detail": ",".join(receipt.get("blocking_reasons") or []),
            }
        ],
        "model_dataset_snapshot": [
            {
                "snapshot_id": snapshot_id,
                "model_id": "current_six_model_chain",
                "request_id": f"request_{run_id}",
                "feature_schema": CURRENT_MODEL_HISTORICAL_SCHEMA,
                "feature_table": f"trading_data.{TARGET_STATE_FEATURE_TABLE}",
                "data_start_time": start,
                "data_end_time": end,
                "feature_row_count": len(examples),
                "feature_data_hash": _stable_id("feature_hash", *(example["target_candidate_id"] + example["available_time"] for example in examples)),
                "model_config_hash": _stable_id("config_hash", CURRENT_MODEL_HISTORICAL_SCHEMA, BASELINE_FEATURE_NAMES),
                "snapshot_payload_json": {"folds": list(folds), "label_name": "future_target_return_1W"},
            }
        ],
        "model_dataset_split": [
            {
                "split_id": str(fold["split_id"]),
                "snapshot_id": snapshot_id,
                "split_name": str(fold["split_name"]),
                "split_start_time": min(example["available_time"] for example in examples if example["fold_key"] == fold["fold_key"]),
                "split_end_time": max(example["available_time"] for example in examples if example["fold_key"] == fold["fold_key"]),
                "split_order": int(fold["split_order"]),
                "split_payload_json": dict(fold),
            }
            for fold in folds
            if any(example["fold_key"] == fold["fold_key"] for example in examples)
        ],
        "model_eval_label": [
            {
                "label_id": _stable_id("label", snapshot_id, example["target_candidate_id"], example["available_time"]),
                "snapshot_id": snapshot_id,
                "label_name": "future_target_return_1W",
                "target_symbol": example["routing_symbol"],
                "horizon": "1W",
                "available_time": example["available_time"],
                "label_time": example["label_payload"]["label_time"],
                "label_value": example["label_payload"]["future_return_1W"],
                "label_payload_json": example["label_payload"],
            }
            for example in examples
            if example["label_payload"].get("label_matured")
        ],
        "model_eval_run": [
            {
                "eval_run_id": eval_run_id,
                "model_id": "current_six_model_chain",
                "snapshot_id": snapshot_id,
                "run_name": "historical_current_chain_evaluation",
                "model_version": "deterministic_current_chain_plus_baseline",
                "config_hash": _stable_id("config_hash", CURRENT_MODEL_HISTORICAL_SCHEMA, BASELINE_FEATURE_NAMES),
                "run_status": "completed" if receipt.get("evaluation_status") == "passed" else "blocked",
                "run_payload_json": dict(receipt),
                "started_at": start,
                "completed_at": end,
                "status_detail": ",".join(receipt.get("blocking_reasons") or []),
            }
        ],
        "model_promotion_metric": [
            {
                "metric_id": _stable_id("metric", eval_run_id, metric["split_id"], name),
                "eval_run_id": eval_run_id,
                "split_id": metric["split_id"],
                "label_name": "future_target_return_1W",
                "target_symbol": "",
                "horizon": "1W",
                "factor_name": "current_chain_utility_baseline",
                "metric_name": name,
                "metric_value": value,
                "metric_payload_json": dict(metric),
            }
            for metric in metrics
            for name, value in (
                ("label_coverage_rate", metric["label_coverage_rate"]),
                ("baseline_prediction_mae", metric["baseline_prediction_mae"]),
                ("mean_future_return_1W", metric["mean_future_return_1W"]),
            )
            if value is not None
        ],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        raise ValueError("timestamp is required")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    return value.astimezone(ET).isoformat()


def _month_key(value: Any) -> str:
    parsed = _parse_time(value)
    return f"{parsed.year:04d}-{parsed.month:02d}"


def _float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _signed(value: Any, default: float) -> float:
    return max(-1.0, min(1.0, _float(value, default)))


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mean(values: Sequence[Any]) -> float | None:
    clean = [_float(value, math.nan) for value in values if value is not None]
    clean = [value for value in clean if not math.isnan(value)]
    return round(sum(clean) / len(clean), 8) if clean else None


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


__all__ = [
    "BASELINE_FEATURE_NAMES",
    "CURRENT_MODEL_HISTORICAL_SCHEMA",
    "HistoricalInputRow",
    "TARGET_STATE_FEATURE_TABLE",
    "TARGET_STATE_SOURCE_TABLE",
    "historical_source_row_to_payload",
    "load_historical_rows_from_database",
    "run_historical_current_chain_evaluation",
]

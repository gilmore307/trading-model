from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trading_model.contracts.types import DiscoveryResult, EvaluationResult, PipelineConfig
from trading_model.discovery.cluster import attach_states, fit_candidate_models
from trading_model.discovery.stability import build_stability_report
from trading_model.evaluation.attach import attach_strategy_to_states
from trading_model.evaluation.forward_returns import add_forward_returns
from trading_model.evaluation.winner_mapping import build_winner_mapping
from trading_model.features.base import FEATURE_COLUMNS, build_base_features
from trading_model.features.preprocess import winsorize_and_scale
from trading_model.io.market_data import load_bars
from trading_model.io.strategy_data import load_global_oracle_returns, load_variant_returns
from trading_model.reporting.oracle_gap import build_oracle_gap_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def run_pipeline(config: PipelineConfig) -> tuple[DiscoveryResult, EvaluationResult]:
    output_root = config.output_root / config.symbol
    state_model_version = f"{config.discovery.method}_kauto_v1"

    bars = load_bars(config.trading_data_root, config.symbol, config.data_months)
    feature_frame = build_base_features(bars, config.feature)
    processed = winsorize_and_scale(feature_frame, FEATURE_COLUMNS, config.feature)
    z_feature_columns = [f"z_{col}" for col in FEATURE_COLUMNS]

    bundle, selection_records = fit_candidate_models(processed[z_feature_columns].to_numpy(), config.discovery)
    state_table = attach_states(processed, bundle, z_feature_columns)
    state_table = add_forward_returns(state_table)

    model_selection_df = pd.DataFrame(record.model_dump() for record in selection_records).sort_values(["score", "k"], ascending=[False, True])
    stability_report = build_stability_report(state_table, model_selection_df, state_model_version)

    state_table_path = output_root / "state_table.csv"
    model_selection_path = output_root / "model_selection.csv"
    stability_report_path = output_root / "stability_report.json"
    _write_csv(state_table_path, state_table)
    _write_csv(model_selection_path, model_selection_df)
    _write_json(stability_report_path, stability_report)

    discovery_result = DiscoveryResult(
        state_table_path=state_table_path,
        model_selection_path=model_selection_path,
        stability_report_path=stability_report_path,
        selected_method=config.discovery.method,
        selected_k=int(state_table["state_id"].nunique()),
        state_model_version=state_model_version,
    )

    variant_returns = load_variant_returns(config.trading_strategy_root, config.symbol, config.strategy_months)
    oracle_returns = load_global_oracle_returns(config.trading_strategy_root, config.symbol, config.strategy_months)
    state_evaluation_table = attach_strategy_to_states(state_table, variant_returns, oracle_returns)
    mapping = build_winner_mapping(state_evaluation_table, config.evaluation)
    oracle_gap_report = build_oracle_gap_report(state_evaluation_table, mapping)

    state_evaluation_table_path = output_root / "state_evaluation_table.csv"
    mapping_path = output_root / "winner_mapping.csv"
    oracle_gap_report_path = output_root / "oracle_gap_report.json"
    _write_csv(state_evaluation_table_path, state_evaluation_table)
    _write_csv(mapping_path, mapping)
    _write_json(oracle_gap_report_path, oracle_gap_report)

    evaluation_result = EvaluationResult(
        state_evaluation_table_path=state_evaluation_table_path,
        mapping_path=mapping_path,
        oracle_gap_report_path=oracle_gap_report_path,
        mapping_version="v1",
    )
    return discovery_result, evaluation_result

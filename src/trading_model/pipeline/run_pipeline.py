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
from trading_model.io.partitions import write_partitioned_csv, write_partitioned_json_object, write_partitioned_json_records
from trading_model.io.strategy_data import load_global_oracle_returns, load_variant_returns
from trading_model.reporting.aggregate_verdict import build_aggregate_cross_symbol_verdict
from trading_model.reporting.baselines import build_trivial_baselines
from trading_model.reporting.execution_confidence import add_execution_confidence_fields
from trading_model.reporting.oracle_gap import build_oracle_gap_report
from trading_model.reporting.research_verdict import build_research_verdict
from trading_model.reporting.trivial_policy import build_trivial_baseline_policy
from trading_model.utils.time import month_label_utc


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
    baselines = build_trivial_baselines(state_table)
    state_table = state_table.merge(baselines, on=["symbol", "ts"], how="left")

    model_selection_df = pd.DataFrame(record.model_dump() for record in selection_records).sort_values(["score", "k"], ascending=[False, True])
    stability_report = build_stability_report(state_table, model_selection_df, state_model_version)

    state_table_partition_root = output_root / "partitions" / "state_table"
    model_selection_path = output_root / "model_selection.csv"
    stability_report_path = output_root / "stability_report.json"
    _write_csv(model_selection_path, model_selection_df)
    _write_json(stability_report_path, stability_report)
    write_partitioned_csv(state_table, state_table_partition_root, partition_cols=["symbol", "month"], filename="state_table.csv")
    write_partitioned_csv(
        model_selection_df.assign(symbol=config.symbol, state_model_version=state_model_version),
        output_root / "partitions" / "model_selection",
        partition_cols=["symbol", "state_model_version"],
        filename="model_selection.csv",
    )
    write_partitioned_json_object(
        stability_report,
        output_root / "partitions" / "stability_report",
        partition_values={"symbol": config.symbol, "state_model_version": state_model_version},
        filename="stability_report.json",
    )

    discovery_result = DiscoveryResult(
        state_table_partition_root=state_table_partition_root,
        model_selection_path=model_selection_path,
        stability_report_path=stability_report_path,
        selected_method=config.discovery.method,
        selected_k=int(state_table["state_id"].nunique()),
        state_model_version=state_model_version,
    )

    variant_returns = load_variant_returns(
        config.trading_strategy_root,
        config.symbol,
        config.strategy_months,
        variant_limit=config.variant_limit,
    )
    oracle_returns = load_global_oracle_returns(config.trading_strategy_root, config.symbol, config.strategy_months)
    state_evaluation_table = attach_strategy_to_states(
        state_table,
        variant_returns,
        oracle_returns,
        tolerance_ms=config.attach_tolerance_ms,
        research_object_type=config.research_object_type,
    )

    trivial_policy, trivial_realized = build_trivial_baseline_policy(state_evaluation_table)
    state_evaluation_table = state_evaluation_table.merge(
        trivial_realized,
        on=["symbol", "ts", "trivial_baseline_id"],
        how="left",
    )

    mapping = build_winner_mapping(state_evaluation_table, config.evaluation)
    mapping = add_execution_confidence_fields(mapping)
    oracle_gap_report = build_oracle_gap_report(state_evaluation_table, mapping)
    research_verdict = build_research_verdict(state_evaluation_table, mapping, trivial_policy)

    state_evaluation_table_partition_root = output_root / "partitions" / "state_evaluation_table"
    mapping_path = output_root / "winner_mapping.csv"
    oracle_gap_report_path = output_root / "oracle_gap_report.json"
    trivial_policy_path = output_root / "trivial_baseline_policy.csv"
    research_verdict_path = output_root / "research_verdict.json"
    _write_csv(mapping_path, mapping)
    _write_csv(trivial_policy_path, trivial_policy)
    _write_json(oracle_gap_report_path, oracle_gap_report)
    _write_json(research_verdict_path, research_verdict)
    write_partitioned_csv(
        state_evaluation_table.assign(month=month_label_utc(state_evaluation_table["timestamp"])),
        state_evaluation_table_partition_root,
        partition_cols=["symbol", "family_id", "variant_id", "month"],
        filename="state_evaluation_table.csv",
    )
    write_partitioned_csv(mapping.assign(symbol=config.symbol), output_root / "partitions" / "winner_mapping", partition_cols=["symbol", "mapping_version"], filename="winner_mapping.csv")
    write_partitioned_csv(
        trivial_policy.assign(symbol=config.symbol),
        output_root / "partitions" / "trivial_baseline_policy",
        partition_cols=["symbol", "trivial_baseline_id"],
        filename="trivial_baseline_policy.csv",
    )
    write_partitioned_json_records(
        oracle_gap_report.get("by_month", []),
        output_root / "partitions" / "oracle_gap_report_by_month",
        partition_cols=["symbol", "month"],
        filename="oracle_gap_report.json",
    )
    write_partitioned_json_records(
        oracle_gap_report.get("by_state", []),
        output_root / "partitions" / "oracle_gap_report_by_state",
        partition_cols=["symbol", "winner_type", "preferred_target"],
        filename="oracle_gap_report.json",
    )
    write_partitioned_json_object(
        {
            "overall": oracle_gap_report.get("overall"),
            "attach_audit": oracle_gap_report.get("attach_audit"),
        },
        output_root / "partitions" / "oracle_gap_report_summary",
        partition_values={"symbol": config.symbol},
        filename="oracle_gap_report_summary.json",
    )
    research_verdict_partition_month = "multi" if len(config.strategy_months) != 1 else config.strategy_months[0]
    write_partitioned_json_object(
        research_verdict,
        output_root / "partitions" / "research_verdict",
        partition_values={"symbol": config.symbol, "month_scope": research_verdict_partition_month},
        filename="research_verdict.json",
    )

    evaluation_result = EvaluationResult(
        state_evaluation_table_partition_root=state_evaluation_table_partition_root,
        mapping_path=mapping_path,
        oracle_gap_report_path=oracle_gap_report_path,
        mapping_version="v1",
    )
    return discovery_result, evaluation_result

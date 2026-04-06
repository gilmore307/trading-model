from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trading_model.contracts.types import PipelineConfig
from trading_model.io.availability import scan_symbol_month_availability
from trading_model.io.partitions import write_partitioned_csv, write_partitioned_json_object
from trading_model.pipeline.run_pipeline import run_pipeline
from trading_model.reporting.aggregate_verdict import build_aggregate_cross_symbol_verdict


def run_multi_symbol_summary(
    *,
    trading_data_root: Path,
    trading_strategy_root: Path,
    output_root: Path,
    symbols: list[str],
    variant_limit: int = 12,
) -> dict:
    availability = scan_symbol_month_availability(trading_data_root, trading_strategy_root, symbols)
    results: list[dict] = []

    for row in availability.to_dict(orient="records"):
        shared_months = row["shared_months"]
        if len(shared_months) < 1:
            results.append({
                "symbol": row["symbol"],
                "status": "skipped_no_shared_months",
                "shared_months": shared_months,
            })
            continue

        config = PipelineConfig(
            symbol=row["symbol"],
            data_months=shared_months,
            strategy_months=shared_months,
            output_root=output_root,
            variant_limit=variant_limit,
        )
        run_pipeline(config)
        verdict_path = output_root / row["symbol"] / "research_verdict.json"
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        results.append(
            {
                "symbol": row["symbol"],
                "status": "ok",
                "shared_months": shared_months,
                "shared_month_count": len(shared_months),
                "state_model_beats_trivial_baseline": verdict["headline"]["state_model_beats_trivial_baseline"],
                "state_model_metric_12bar": verdict["headline"]["state_model_metric_12bar"],
                "trivial_baseline_metric_12bar": verdict["headline"]["trivial_baseline_metric_12bar"],
                "oracle_metric_12bar": verdict["headline"]["oracle_metric_12bar"],
                "accepted_winner_state_count": verdict["mapping_summary"]["accepted_winner_state_count"],
                "blocked_state_count": verdict["mapping_summary"]["blocked_state_count"],
                "execution_confidence_mean": verdict.get("execution_confidence_summary", {}).get("mean"),
                "execution_confidence_max": verdict.get("execution_confidence_summary", {}).get("max"),
            }
        )

    summary = {
        "availability": availability.to_dict(orient="records"),
        "results": results,
    }
    aggregate_verdict = build_aggregate_cross_symbol_verdict(summary)
    summary["aggregate_verdict"] = aggregate_verdict
    summary_path = output_root / "multi_symbol_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_root / "multi_symbol_summary.csv", index=False)
    (output_root / "aggregate_cross_symbol_verdict.json").write_text(json.dumps(aggregate_verdict, ensure_ascii=False, indent=2), encoding="utf-8")

    if not results_df.empty:
        write_partitioned_csv(
            results_df,
            output_root / "partitions" / "multi_symbol_summary",
            partition_cols=["symbol"],
            filename="multi_symbol_summary.csv",
        )
    write_partitioned_json_object(
        summary,
        output_root / "partitions" / "multi_symbol_summary_full",
        partition_values={"scope": "all"},
        filename="multi_symbol_summary.json",
    )
    write_partitioned_json_object(
        aggregate_verdict,
        output_root / "partitions" / "aggregate_cross_symbol_verdict",
        partition_values={"scope": "all"},
        filename="aggregate_cross_symbol_verdict.json",
    )
    return summary

#!/usr/bin/env python3
"""Compare online and MLP continual candidates on one historical fold.

This script is model-side experiment evidence only. It reads existing
point-in-time rows, writes a local comparison artifact, and never promotes,
activates, calls providers, mutates SQL, or touches broker/account state.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from model_governance.historical_current_chain_evaluation import (
    BASELINE_FEATURE_NAMES,
    build_historical_current_chain_examples,
    load_historical_rows_from_database,
)
from model_governance.training import (
    chronological_month_splits,
    predict_mlp,
    predict_online_linear,
    regression_metrics,
    standardize_by_train,
    train_mlp_regressor,
    train_online_linear_regressor,
)
from model_runtime.config import database_url_file, model_storage_root


DEFAULT_DB_URL_FILE = database_url_file()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--target-symbol", default="AAPL")
    parser.add_argument("--start-time", default="2016-01-01T00:00:00-05:00")
    parser.add_argument("--end-time", default="2016-08-01T00:00:00-04:00")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--per-month-limit", type=int, default=400)
    parser.add_argument("--label-horizon-days", type=int, default=7)
    parser.add_argument("--train-months", type=int, default=4)
    parser.add_argument("--validation-months", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)

    run_id = args.run_id or "continual_candidate_comparison_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target_symbol = args.target_symbol.strip().upper()
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            rows = load_historical_rows_from_database(
                cursor,
                start_time=args.start_time,
                end_time=args.end_time,
                limit=args.limit,
                per_month_limit=args.per_month_limit,
                label_horizon_days=args.label_horizon_days,
            )

    target_rows = [row for row in rows if str(row.source_row.get("symbol") or "").strip().upper() == target_symbol]
    examples, blocked_rows = build_historical_current_chain_examples(target_rows)
    labeled_examples = [example for example in examples if example["label_payload"].get("utility_score_1W") is not None]
    if not labeled_examples:
        raise SystemExit("no labeled examples available for comparison")

    feature_rows = [example["feature_vector"] for example in labeled_examples]
    targets = [float(example["label_payload"]["utility_score_1W"]) for example in labeled_examples]
    fold_keys = [str(example["fold_key"]) for example in labeled_examples]
    splits = chronological_month_splits(
        fold_keys,
        train_months=args.train_months,
        validation_months=args.validation_months,
    )
    train_split = next(split for split in splits if split.name == "train")
    scaled_features, scaler = standardize_by_train(feature_rows, train_split.indexes)

    online_artifact = train_online_linear_regressor(
        feature_rows=scaled_features,
        targets=targets,
        train_indexes=train_split.indexes,
    )
    mlp_artifact = train_mlp_regressor(
        feature_rows=scaled_features,
        targets=targets,
        train_indexes=train_split.indexes,
    )

    predictions = {
        "online_sigmoid_linear_sgd": predict_online_linear(scaled_features, online_artifact),
        "one_hidden_layer_mlp_sgd": predict_mlp(scaled_features, mlp_artifact),
    }
    split_metrics = {
        model_name: {
            split.name: regression_metrics(
                [targets[index] for index in split.indexes],
                [model_predictions[index] for index in split.indexes],
            )
            for split in splits
        }
        for model_name, model_predictions in predictions.items()
    }
    receipt = {
        "contract_type": "continual_model_candidate_comparison_receipt",
        "schema_version": "2026-06-27",
        "run_id": run_id,
        "target_symbol": target_symbol,
        "source_window": {
            "start_time": args.start_time,
            "end_time": args.end_time,
            "label_horizon_days": args.label_horizon_days,
        },
        "split_policy": {
            "name": "chronological_rolling_fold_4_1_1",
            "train_months": args.train_months,
            "validation_months": args.validation_months,
            "splits": [
                {"name": split.name, "fold_keys": list(split.fold_keys), "row_count": len(split.indexes)}
                for split in splits
            ],
        },
        "row_counts": {
            "source_rows": len(rows),
            "target_source_rows": len(target_rows),
            "generated_examples": len(examples),
            "blocked_examples": len(blocked_rows),
            "labeled_examples": len(labeled_examples),
        },
        "feature_names": list(BASELINE_FEATURE_NAMES),
        "feature_scaler": scaler,
        "models": {
            "online_sigmoid_linear_sgd": _model_summary(online_artifact),
            "one_hidden_layer_mlp_sgd": _model_summary(mlp_artifact),
        },
        "split_metrics": split_metrics,
        "safety": {
            "provider_calls_performed": False,
            "sql_mutation_performed": False,
            "model_activation_performed": False,
            "production_promotion_allowed": False,
            "broker_or_account_mutation_performed": False,
        },
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }

    output_path = args.output_json or default_output_path(run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "succeeded", "output_json": str(output_path), "run_id": run_id}, sort_keys=True))
    return 0


def default_output_path(run_id: str) -> Path:
    return model_storage_root() / "continual_model_candidate_comparison" / run_id / "comparison_receipt.json"


def _model_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: artifact.get(key)
        for key in ("model_id", "model_type", "model_version", "seed", "epochs", "iterations", "learning_rate", "l2", "hidden_units", "training_summary")
        if key in artifact
    }


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for continual candidate comparison; install psycopg[binary].") from error
    return psycopg, dict_row


if __name__ == "__main__":
    raise SystemExit(main())

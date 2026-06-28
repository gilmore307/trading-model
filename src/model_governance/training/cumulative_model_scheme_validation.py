"""Replayable cumulative model scheme validation contracts."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .continual_residual_mlp import (
    DatasetSplit,
    chronological_month_splits,
    predict_mlp,
    regression_metrics,
    standardize_by_train,
    train_mlp_regressor,
)


EXPERIMENT_CONTRACT_TYPE = "cumulative_model_scheme_validation_receipt"
EXPERIMENT_SCHEMA_VERSION = "2026-06-28"


VALIDATED_MODEL_SCHEME_ID = "continual_residual_mlp"
VALIDATED_MODEL_IMPLEMENTATION_ID = "one_hidden_layer_mlp_sgd"


LAYER_ACTIVE_SCHEME_MATRIX: tuple[dict[str, str], ...] = (
    {
        "layer": "M01 BackgroundContextModel",
        "active_scheme": "continual_residual_mlp_context_classifier",
        "structure": "hashed-feature residual MLP classifier/embedding model over point-in-time market, sector, liquidity, volatility, macro, and cross-asset state",
        "deciding_metrics": "calibration; regime-transition accuracy; volatility/liquidity error; downstream lift",
    },
    {
        "layer": "M02 TargetStateModel",
        "active_scheme": "continual_residual_mlp_target_ranker",
        "structure": "pairwise/listwise residual MLP ranker over anonymous target-state vectors",
        "deciding_metrics": "rank IC/NDCG; calibrated eligibility; identity-leakage probe; target-selection utility",
    },
    {
        "layer": "M03 EventStateModel",
        "active_scheme": "continual_residual_mlp_event_risk_scorer",
        "structure": "multi-head residual MLP event-risk scorer over reviewed structured event features",
        "deciding_metrics": "event calibration; response/risk loss; tail-risk recall; no same-fold M06 leakage",
    },
    {
        "layer": "M04 UnifiedDecisionModel",
        "active_scheme": "continual_residual_mlp_policy_value",
        "structure": "conservative supervised/off-policy residual MLP policy-value model over chain state, costs, risk, exposure, and portfolio context",
        "deciding_metrics": "after-cost utility; no-trade calibration; downside risk; turnover; chain PnL/risk",
    },
    {
        "layer": "M05 OptionExpressionModel",
        "active_scheme": "continual_residual_mlp_option_chain_ranker",
        "structure": "residual MLP option-chain ranker over option-relative features, Greeks, liquidity, spread, surface, horizon, and expression state",
        "deciding_metrics": "option after-cost utility; fill realism; top-k ranking; no-option calibration",
    },
    {
        "layer": "M06 ResidualEventGovernanceModel",
        "active_scheme": "continual_residual_mlp_risk_gate",
        "structure": "calibrated residual MLP risk-gate/intervention scorer with abstain, block, size-down, and allow outputs plus deterministic hard guardrails",
        "deciding_metrics": "missed-event loss; overblock cost; attribution precision/recall; packet quality",
    },
)


def build_cumulative_model_scheme_validation_receipt(
    examples: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
    feature_names: Sequence[str],
    label_proxy: str = "current_chain_utility_score_1W",
    train_months: int = 4,
    validation_months: int = 1,
    minimum_symbols: int = 3,
) -> dict[str, Any]:
    """Build selected cumulative model scheme validation evidence from current-chain examples."""

    labeled = [example for example in examples if _label(example) is not None]
    symbols = sorted({str(example.get("routing_symbol") or "").upper() for example in labeled if example.get("routing_symbol")})
    fold_keys = [str(example.get("fold_key") or "") for example in labeled]
    blocked_reasons: list[str] = []
    if len(symbols) < minimum_symbols:
        blocked_reasons.append("insufficient_symbol_diversity_for_identity_probe")
    if not labeled:
        blocked_reasons.append("no_labeled_examples")
    splits: list[DatasetSplit] = []
    if labeled:
        try:
            splits = chronological_month_splits(
                fold_keys,
                train_months=train_months,
                validation_months=validation_months,
            )
        except ValueError as error:
            blocked_reasons.append(str(error))

    if blocked_reasons or not labeled or not splits:
        return _blocked_receipt(
            run_id=run_id,
            feature_names=feature_names,
            examples=examples,
            labeled=labeled,
            symbols=symbols,
            blocked_reasons=blocked_reasons,
            train_months=train_months,
            validation_months=validation_months,
        )

    train_split = next(split for split in splits if split.name == "train")
    feature_rows = [list(example["feature_vector"]) for example in labeled]
    targets = [float(_label(example)) for example in labeled]
    scaled_features, scaler = standardize_by_train(feature_rows, train_split.indexes)
    artifacts = {
        VALIDATED_MODEL_SCHEME_ID: train_mlp_regressor(
            feature_rows=scaled_features,
            targets=targets,
            train_indexes=train_split.indexes,
        ),
    }
    predictions = {
        VALIDATED_MODEL_SCHEME_ID: predict_mlp(scaled_features, artifacts[VALIDATED_MODEL_SCHEME_ID]),
    }
    split_metrics = {
        model_id: {
            split.name: regression_metrics(
                [targets[index] for index in split.indexes],
                [model_predictions[index] for index in split.indexes],
            )
            for split in splits
        }
        for model_id, model_predictions in predictions.items()
    }
    checkpoint_checks = {
        model_id: _checkpoint_restore_check(
            model_id=model_id,
            scaler=scaler,
            artifact=artifacts[model_id],
            scaled_features=scaled_features,
            original_predictions=predictions[model_id],
        )
        for model_id in artifacts
    }
    identity_probe = _identity_leakage_probe(
        scaled_features=scaled_features,
        feature_names=feature_names,
        symbols=[str(example.get("routing_symbol") or "").upper() for example in labeled],
        splits=splits,
    )
    leakage_passed = identity_probe["status"] == "passed"
    scheme_verdict = {
        model_id: {
            "scheme_viable": checkpoint_checks[model_id]["passed"] and leakage_passed,
            "promotion_ready": False,
            "promotion_blockers": [
                "initial_scheme_validation_only",
                "full_chain_replay_not_yet_run",
                "layer_specific_labels_not_yet_complete",
            ]
            + ([] if leakage_passed else ["identity_leakage_probe_not_passed"]),
            "role": "validated_cumulative_model_scheme",
            "implementation_id": VALIDATED_MODEL_IMPLEMENTATION_ID,
        }
        for model_id in artifacts
    }

    return {
        "contract_type": EXPERIMENT_CONTRACT_TYPE,
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "run_id": run_id,
        "experiment_scope": {
            "name": "cumulative_residual_mlp_scheme_validation",
            "evidence_level": "scheme_viability_not_promotion",
            "label_proxy": label_proxy,
            "scheme_validation_completed": True,
            "validated_model_scheme": VALIDATED_MODEL_SCHEME_ID,
        },
        "row_counts": {
            "generated_examples": len(examples),
            "labeled_examples": len(labeled),
            "unique_symbols": len(symbols),
            "unique_folds": len({key for key in fold_keys if key}),
        },
        "symbols": symbols,
        "feature_names": list(feature_names),
        "split_policy": {
            "name": "chronological_rolling_fold",
            "train_months": train_months,
            "validation_months": validation_months,
            "splits": [
                {"name": split.name, "fold_keys": list(split.fold_keys), "row_count": len(split.indexes)}
                for split in splits
            ],
        },
        "layer_active_scheme_matrix": list(LAYER_ACTIVE_SCHEME_MATRIX),
        "selected_model": {
            model_id: _model_summary(artifacts[model_id])
            for model_id in artifacts
        },
        "feature_scaler_checkpoint": scaler,
        "split_metrics": split_metrics,
        "checkpoint_restore_checks": checkpoint_checks,
        "identity_leakage_probe": identity_probe,
        "scheme_verdict": scheme_verdict,
        "selection_rule": {
            "validated_scheme": VALIDATED_MODEL_SCHEME_ID,
            "per_layer_single_active_policy": "one_active_model_scheme_per_layer_no_parallel_runtime_challengers",
            "implementation_note": "This receipt validates the cumulative residual MLP family; each layer uses the active scheme listed in layer_active_scheme_matrix.",
            "promotion_requires": [
                "layer_specific_objective_lift",
                "full_chain_replay_neutral_or_positive",
                "walk_forward_stability",
                "cost_and_fill_stress_for_m04_m05",
            ],
        },
        "safety": {
            "provider_calls_performed": False,
            "sql_mutation_performed": False,
            "model_activation_performed": False,
            "production_promotion_allowed": False,
            "broker_or_account_mutation_performed": False,
        },
    }


def _blocked_receipt(
    *,
    run_id: str,
    feature_names: Sequence[str],
    examples: Sequence[Mapping[str, Any]],
    labeled: Sequence[Mapping[str, Any]],
    symbols: Sequence[str],
    blocked_reasons: Sequence[str],
    train_months: int,
    validation_months: int,
) -> dict[str, Any]:
    return {
        "contract_type": EXPERIMENT_CONTRACT_TYPE,
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "run_id": run_id,
        "experiment_scope": {
            "name": "cumulative_residual_mlp_scheme_validation",
            "evidence_level": "blocked",
            "scheme_validation_completed": False,
        },
        "row_counts": {
            "generated_examples": len(examples),
            "labeled_examples": len(labeled),
            "unique_symbols": len(symbols),
        },
        "symbols": list(symbols),
        "feature_names": list(feature_names),
        "split_policy": {
            "name": "chronological_rolling_fold",
            "train_months": train_months,
            "validation_months": validation_months,
        },
        "layer_active_scheme_matrix": list(LAYER_ACTIVE_SCHEME_MATRIX),
        "scheme_verdict": {},
        "blocked_reasons": list(blocked_reasons),
        "safety": {
            "provider_calls_performed": False,
            "sql_mutation_performed": False,
            "model_activation_performed": False,
            "production_promotion_allowed": False,
            "broker_or_account_mutation_performed": False,
        },
    }


def _checkpoint_restore_check(
    *,
    model_id: str,
    scaler: Mapping[str, Any],
    artifact: Mapping[str, Any],
    scaled_features: Sequence[Sequence[float]],
    original_predictions: Sequence[float],
) -> dict[str, Any]:
    checkpoint = json.loads(json.dumps({"feature_scaler": scaler, "model": artifact}, sort_keys=True))
    restored_model = checkpoint["model"]
    restored_predictions = predict_mlp(scaled_features, restored_model)
    max_delta = max((abs(a - b) for a, b in zip(original_predictions, restored_predictions)), default=0.0)
    return {
        "passed": max_delta <= 1e-12,
        "max_prediction_delta": round(max_delta, 16),
        "checkpoint_contains_scaler": bool(checkpoint.get("feature_scaler", {}).get("mean"))
        and bool(checkpoint.get("feature_scaler", {}).get("std")),
    }


def _identity_leakage_probe(
    *,
    scaled_features: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    symbols: Sequence[str],
    splits: Sequence[DatasetSplit],
) -> dict[str, Any]:
    disallowed_tokens = ("symbol", "ticker", "target_candidate_id", "security_id", "isin", "cusip")
    identifier_features = [
        name for name in feature_names
        if any(token in str(name).lower() for token in disallowed_tokens)
    ]
    unique_symbols = sorted({symbol for symbol in symbols if symbol})
    if len(unique_symbols) < 2:
        return {
            "status": "failed" if identifier_features else "skipped",
            "reason": "requires_at_least_two_symbols",
            "direct_identifier_feature_check": {
                "status": "failed" if identifier_features else "passed",
                "identifier_features": identifier_features,
            },
        }
    train_split = next(split for split in splits if split.name == "train")
    centroids = _symbol_centroids(scaled_features, symbols, train_split.indexes)
    if len(centroids) < 2:
        return {
            "status": "failed" if identifier_features else "skipped",
            "reason": "requires_at_least_two_train_symbols",
            "direct_identifier_feature_check": {
                "status": "failed" if identifier_features else "passed",
                "identifier_features": identifier_features,
            },
        }
    random_baseline = 1.0 / len(centroids)
    warning_threshold = max(0.5, random_baseline + 0.2)
    split_results: dict[str, Any] = {}
    max_eval_accuracy = 0.0
    for split in splits:
        accuracy = _nearest_centroid_accuracy(scaled_features, symbols, split.indexes, centroids)
        split_results[split.name] = {
            "row_count": len(split.indexes),
            "nearest_centroid_symbol_accuracy": round(accuracy, 8) if accuracy is not None else None,
        }
        if split.name != "train" and accuracy is not None:
            max_eval_accuracy = max(max_eval_accuracy, accuracy)
    centroid_status = "within_warning_threshold" if max_eval_accuracy <= warning_threshold else "high_symbol_separability_warning"
    status = "failed" if identifier_features else "passed"
    return {
        "status": status,
        "contract": "target_anonymous_not_target_blind",
        "direct_identifier_feature_check": {
            "status": "failed" if identifier_features else "passed",
            "identifier_features": identifier_features,
        },
        "centroid_symbol_separability_diagnostic": {
            "status": centroid_status,
            "method": "nearest_train_symbol_centroid_over_model_features",
            "trained_symbol_count": len(centroids),
            "random_baseline_accuracy": round(random_baseline, 8),
            "warning_threshold": round(warning_threshold, 8),
            "max_eval_accuracy": round(max_eval_accuracy, 8),
            "split_results": split_results,
            "interpretation": "A state vector may still be symbol-separable through price, liquidity, volatility, or spread. That is a diagnostic warning, not raw identifier leakage.",
        },
    }


def _symbol_centroids(
    features: Sequence[Sequence[float]],
    symbols: Sequence[str],
    indexes: Sequence[int],
) -> dict[str, list[float]]:
    sums: dict[str, list[float]] = {}
    counts: defaultdict[str, int] = defaultdict(int)
    for index in indexes:
        symbol = symbols[index]
        if not symbol:
            continue
        row = [float(value) for value in features[index]]
        if symbol not in sums:
            sums[symbol] = [0.0 for _value in row]
        for offset, value in enumerate(row):
            sums[symbol][offset] += value
        counts[symbol] += 1
    return {
        symbol: [value / counts[symbol] for value in totals]
        for symbol, totals in sums.items()
        if counts[symbol] > 0
    }


def _nearest_centroid_accuracy(
    features: Sequence[Sequence[float]],
    symbols: Sequence[str],
    indexes: Sequence[int],
    centroids: Mapping[str, Sequence[float]],
) -> float | None:
    scored = 0
    correct = 0
    for index in indexes:
        actual = symbols[index]
        if actual not in centroids:
            continue
        predicted = min(
            centroids,
            key=lambda symbol: _squared_distance(features[index], centroids[symbol]),
        )
        scored += 1
        correct += int(predicted == actual)
    if scored == 0:
        return None
    return correct / scored


def _squared_distance(left: Sequence[float], right: Sequence[float]) -> float:
    return sum((float(a) - float(b)) ** 2 for a, b in zip(left, right))


def _label(example: Mapping[str, Any]) -> float | None:
    label = example.get("label_payload")
    if not isinstance(label, Mapping):
        return None
    value = label.get("utility_score_1W")
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _model_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: artifact.get(key)
        for key in ("model_type", "seed", "epochs", "learning_rate", "l2", "hidden_units")
        if key in artifact
    }


__all__ = [
    "EXPERIMENT_CONTRACT_TYPE",
    "EXPERIMENT_SCHEMA_VERSION",
    "VALIDATED_MODEL_IMPLEMENTATION_ID",
    "VALIDATED_MODEL_SCHEME_ID",
    "LAYER_ACTIVE_SCHEME_MATRIX",
    "build_cumulative_model_scheme_validation_receipt",
]

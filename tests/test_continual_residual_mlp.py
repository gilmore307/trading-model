from __future__ import annotations

import unittest

from model_governance.training import (
    EXPERIMENT_CONTRACT_TYPE,
    LAYER_ACTIVE_SCHEME_MATRIX,
    VALIDATED_MODEL_SCHEME_ID,
    build_cumulative_model_scheme_validation_receipt,
    chronological_month_splits,
    predict_mlp,
    regression_metrics,
    standardize_by_train,
    train_mlp_regressor,
)


class ContinualResidualMlpTests(unittest.TestCase):
    def test_chronological_month_splits_uses_rolling_4_1_1_shape(self) -> None:
        fold_keys = ["2016-01", "2016-01", "2016-02", "2016-03", "2016-04", "2016-05", "2016-06"]

        splits = chronological_month_splits(fold_keys, train_months=4, validation_months=1)

        self.assertEqual([split.name for split in splits], ["train", "validation", "test"])
        self.assertEqual(splits[0].fold_keys, ("2016-01", "2016-02", "2016-03", "2016-04"))
        self.assertEqual(splits[0].indexes, (0, 1, 2, 3, 4))
        self.assertEqual(splits[1].fold_keys, ("2016-05",))
        self.assertEqual(splits[2].fold_keys, ("2016-06",))

    def test_selected_mlp_scheme_returns_bounded_predictions(self) -> None:
        features = [
            [0.0, 0.0],
            [0.2, 0.1],
            [0.8, 0.7],
            [1.0, 0.9],
            [0.1, 0.2],
            [0.9, 1.0],
        ]
        targets = [0.2, 0.25, 0.75, 0.8, 0.3, 0.85]
        train_indexes = (0, 1, 2, 3)
        scaled, scaler = standardize_by_train(features, train_indexes)

        mlp = train_mlp_regressor(feature_rows=scaled, targets=targets, train_indexes=train_indexes, epochs=10, hidden_units=4)
        mlp_predictions = predict_mlp(scaled, mlp)

        self.assertEqual(len(scaler["mean"]), 2)
        self.assertEqual(len(mlp_predictions), len(features))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in mlp_predictions))

    def test_regression_metrics_reports_error_and_direction(self) -> None:
        metrics = regression_metrics([0.2, 0.8], [0.3, 0.7])

        self.assertEqual(metrics["row_count"], 2)
        self.assertEqual(metrics["mae"], 0.1)
        self.assertEqual(metrics["directional_accuracy_vs_neutral"], 1.0)

    def test_cumulative_model_scheme_validation_receipt_proves_selected_contract(self) -> None:
        examples = []
        months = ("2016-01", "2016-02", "2016-03", "2016-04")
        symbols = ("AAPL", "MSFT", "NVDA")
        for month_index, month in enumerate(months):
            for symbol_index, symbol in enumerate(symbols):
                examples.append(
                    {
                        "routing_symbol": symbol,
                        "fold_key": month,
                        "feature_vector": [
                            0.1 * month_index,
                            0.2 * symbol_index,
                            0.05 * (month_index + symbol_index),
                        ],
                        "label_payload": {"utility_score_1W": 0.35 + 0.05 * month_index + 0.02 * symbol_index},
                    }
                )

        receipt = build_cumulative_model_scheme_validation_receipt(
            examples,
            run_id="unit_test_scheme_validation",
            feature_names=("f1", "f2", "f3"),
            train_months=2,
            validation_months=1,
        )

        self.assertEqual(receipt["contract_type"], EXPERIMENT_CONTRACT_TYPE)
        self.assertTrue(receipt["experiment_scope"]["scheme_validation_completed"])
        self.assertEqual(receipt["row_counts"]["unique_symbols"], 3)
        self.assertEqual(receipt["experiment_scope"]["validated_model_scheme"], VALIDATED_MODEL_SCHEME_ID)
        self.assertEqual(
            [row["active_scheme"] for row in receipt["layer_active_scheme_matrix"]],
            [row["active_scheme"] for row in LAYER_ACTIVE_SCHEME_MATRIX],
        )
        self.assertEqual(
            [row["active_scheme"] for row in LAYER_ACTIVE_SCHEME_MATRIX],
            [
                "continual_residual_mlp_context_classifier",
                "continual_residual_mlp_target_ranker",
                "continual_residual_mlp_event_risk_scorer",
                "continual_residual_mlp_policy_value",
                "continual_residual_mlp_option_chain_ranker",
                "continual_residual_mlp_risk_gate",
            ],
        )
        self.assertIn(VALIDATED_MODEL_SCHEME_ID, receipt["scheme_verdict"])
        self.assertEqual(tuple(receipt["scheme_verdict"]), (VALIDATED_MODEL_SCHEME_ID,))
        self.assertTrue(receipt["checkpoint_restore_checks"][VALIDATED_MODEL_SCHEME_ID]["passed"])
        self.assertEqual(receipt["identity_leakage_probe"]["status"], "passed")
        self.assertFalse(receipt["scheme_verdict"][VALIDATED_MODEL_SCHEME_ID]["promotion_ready"])
        self.assertFalse(receipt["safety"]["production_promotion_allowed"])

    def test_cumulative_model_scheme_validation_blocks_single_symbol_evidence(self) -> None:
        examples = [
            {
                "routing_symbol": "AAPL",
                "fold_key": "2016-01",
                "feature_vector": [0.1, 0.2],
                "label_payload": {"utility_score_1W": 0.55},
            },
            {
                "routing_symbol": "AAPL",
                "fold_key": "2016-02",
                "feature_vector": [0.2, 0.3],
                "label_payload": {"utility_score_1W": 0.57},
            },
        ]

        receipt = build_cumulative_model_scheme_validation_receipt(
            examples,
            run_id="unit_test_blocked",
            feature_names=("f1", "f2"),
            train_months=1,
            validation_months=1,
        )

        self.assertEqual(receipt["experiment_scope"]["evidence_level"], "blocked")
        self.assertIn("insufficient_symbol_diversity_for_identity_probe", receipt["blocked_reasons"])


if __name__ == "__main__":
    unittest.main()

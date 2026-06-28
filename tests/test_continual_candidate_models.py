from __future__ import annotations

import unittest

from model_governance.training import (
    chronological_month_splits,
    predict_mlp,
    predict_online_linear,
    regression_metrics,
    standardize_by_train,
    train_mlp_regressor,
    train_online_linear_regressor,
)


class ContinualCandidateModelTests(unittest.TestCase):
    def test_chronological_month_splits_uses_rolling_4_1_1_shape(self) -> None:
        fold_keys = ["2016-01", "2016-01", "2016-02", "2016-03", "2016-04", "2016-05", "2016-06"]

        splits = chronological_month_splits(fold_keys, train_months=4, validation_months=1)

        self.assertEqual([split.name for split in splits], ["train", "validation", "test"])
        self.assertEqual(splits[0].fold_keys, ("2016-01", "2016-02", "2016-03", "2016-04"))
        self.assertEqual(splits[0].indexes, (0, 1, 2, 3, 4))
        self.assertEqual(splits[1].fold_keys, ("2016-05",))
        self.assertEqual(splits[2].fold_keys, ("2016-06",))

    def test_online_and_mlp_candidates_return_bounded_predictions(self) -> None:
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

        online = train_online_linear_regressor(feature_rows=scaled, targets=targets, train_indexes=train_indexes, epochs=10)
        mlp = train_mlp_regressor(feature_rows=scaled, targets=targets, train_indexes=train_indexes, epochs=10, hidden_units=4)
        online_predictions = predict_online_linear(scaled, online)
        mlp_predictions = predict_mlp(scaled, mlp)

        self.assertEqual(len(scaler["mean"]), 2)
        self.assertEqual(len(online_predictions), len(features))
        self.assertEqual(len(mlp_predictions), len(features))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in online_predictions))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in mlp_predictions))

    def test_regression_metrics_reports_error_and_direction(self) -> None:
        metrics = regression_metrics([0.2, 0.8], [0.3, 0.7])

        self.assertEqual(metrics["row_count"], 2)
        self.assertEqual(metrics["mae"], 0.1)
        self.assertEqual(metrics["directional_accuracy_vs_neutral"], 1.0)


if __name__ == "__main__":
    unittest.main()


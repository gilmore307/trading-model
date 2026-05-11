from __future__ import annotations

import unittest

from model_governance.evaluation.persistence import normalize_row


class EvaluationPersistenceTests(unittest.TestCase):
    def test_normalizes_layer_three_label_aliases(self) -> None:
        row = normalize_row(
            "model_eval_label",
            {
                "label_id": "lbl1",
                "snapshot_id": "snap1",
                "label_name": "future_target_tradeable_path",
                "target_symbol": "tcand",
                "label_horizon": "15min",
                "label_available_time": "2018-01-02T00:15:00-05:00",
                "label_value": 1.0,
                "label_payload_json": {"feature_available_time": "2018-01-02T00:00:00-05:00"},
            },
        )
        self.assertEqual(row["horizon"], "15min")
        self.assertEqual(row["available_time"], "2018-01-02T00:00:00-05:00")
        self.assertEqual(row["label_time"], "2018-01-02T00:15:00-05:00")

    def test_normalizes_layer_three_eval_run_aliases(self) -> None:
        row = normalize_row(
            "model_eval_run",
            {
                "eval_run_id": "run1",
                "model_id": "model_03_target_state_vector",
                "snapshot_id": "snap1",
                "eval_status": "completed",
                "eval_payload_json": {"evidence_source": "real_database_evaluation"},
                "eval_started_at": "2018-01-31T16:00:00-05:00",
                "eval_completed_at": "2018-01-31T16:00:00-05:00",
            },
        )
        self.assertEqual(row["run_status"], "completed")
        self.assertEqual(row["run_payload_json"], {"evidence_source": "real_database_evaluation"})
        self.assertEqual(row["started_at"], "2018-01-31T16:00:00-05:00")
        self.assertEqual(row["completed_at"], "2018-01-31T16:00:00-05:00")

    def test_defaults_optional_metric_fields(self) -> None:
        row = normalize_row(
            "model_promotion_metric",
            {
                "metric_id": "metric1",
                "eval_run_id": "run1",
                "metric_name": "label_count",
                "metric_value": 10.0,
            },
        )
        self.assertEqual(row["target_symbol"], "")
        self.assertEqual(row["metric_payload_json"], {})


if __name__ == "__main__":
    unittest.main()

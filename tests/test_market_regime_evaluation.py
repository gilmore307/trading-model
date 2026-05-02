from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from models.model_01_market_regime.evaluation import (
    build_evaluation_artifacts,
    summarize_artifacts,
)

ET = ZoneInfo("America/New_York")


def _rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start = datetime(2026, 1, 2, 16, 0, tzinfo=ET)
    features: list[dict[str, object]] = []
    models: list[dict[str, object]] = []
    for index in range(10):
        timestamp = (start + timedelta(days=index)).isoformat()
        features.append(
            {
                "snapshot_time": timestamp,
                "spy_return_1d": (index - 4) / 100,
                "spy_return_5d": (index - 2) / 50,
            }
        )
        models.append(
            {
                "available_time": timestamp,
                "trend_certainty_factor": (index - 4) / 10,
                "sentiment_factor": (index - 4) / 10,
                "risk_stress_factor": (4 - index) / 10,
                "data_quality_score": 1.0,
            }
        )
    return features, models


class MarketRegimeEvaluationTests(unittest.TestCase):
    def test_builds_governance_artifacts_without_database_dependency(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        table_rows = artifacts.as_table_rows()

        self.assertEqual(len(table_rows["model_dataset_request"]), 1)
        self.assertEqual(len(table_rows["model_dataset_snapshot"]), 1)
        self.assertEqual(len(table_rows["model_dataset_split"]), 3)
        self.assertGreater(len(table_rows["model_eval_label"]), 0)
        self.assertGreater(len(table_rows["model_eval_metric"]), 0)
        self.assertEqual(artifacts.dataset_request["request_status"], "dry_run_only")
        self.assertEqual(artifacts.eval_run["run_status"], "dry_run_only")
        self.assertEqual(artifacts.dataset_request["required_feature_key"], "FEATURE_01_MARKET_REGIME")
        self.assertNotIn("required_derived_key", artifacts.dataset_request)

    def test_splits_are_chronological(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        splits = artifacts.dataset_splits

        self.assertEqual([split["split_name"] for split in splits], ["train", "validation", "test"])
        self.assertLess(splits[0]["split_end_time"], splits[1]["split_start_time"])
        self.assertLess(splits[1]["split_end_time"], splits[2]["split_start_time"])

    def test_future_labels_use_later_feature_rows(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        first_label = next(
            label
            for label in artifacts.eval_labels
            if label["label_name"] == "future_return" and label["horizon"] == "1_step"
        )

        self.assertEqual(first_label["available_time"], features[0]["snapshot_time"])
        self.assertEqual(first_label["label_time"], features[1]["snapshot_time"])
        self.assertEqual(first_label["label_value"], features[1]["spy_return_1d"])

    def test_metrics_include_correlation_and_coverage(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        metric_names = {metric["metric_name"] for metric in artifacts.eval_metrics}

        self.assertIn("label_count", metric_names)
        self.assertIn("pair_count", metric_names)
        self.assertIn("coverage", metric_names)
        self.assertIn("pearson_correlation", metric_names)

    def test_summary_advertises_no_database_write_policy(self) -> None:
        features, models = _rows()
        summary = summarize_artifacts(build_evaluation_artifacts(feature_rows=features, model_rows=models))

        self.assertEqual(summary["write_policy"], "no_database_write")
        self.assertEqual(summary["tables"]["model_dataset_request"], 1)
        self.assertGreater(summary["tables"]["model_eval_metric"], 0)

    def test_dry_run_harness_has_no_database_connection_surface(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        texts = [
            (repo_root / "src" / "models" / "model_01_market_regime" / "evaluation.py").read_text(encoding="utf-8"),
            (repo_root / "scripts" / "evaluate_model_01_market_regime.py").read_text(encoding="utf-8"),
        ]
        forbidden = ["psycopg", "OPENCLAW_DATABASE_URL", "database-url", "connect("]
        for text in texts:
            for token in forbidden:
                self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()

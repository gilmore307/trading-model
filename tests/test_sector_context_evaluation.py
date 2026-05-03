from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from models.model_02_sector_context.evaluation import build_evaluation_artifacts, summarize_artifacts
from model_governance.promotion.agent_review import build_sector_context_promotion_prompt

ET = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATE_SCRIPT = REPO_ROOT / "scripts" / "models" / "model_02_sector_context" / "evaluate_model_02_sector_context.py"
REVIEW_SCRIPT = REPO_ROOT / "scripts" / "models" / "model_02_sector_context" / "review_sector_context_promotion.py"


def _rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start = datetime(2026, 1, 2, 16, 0, tzinfo=ET)
    features: list[dict[str, object]] = []
    models: list[dict[str, object]] = []
    for index in range(10):
        timestamp = (start + timedelta(days=index)).isoformat()
        for symbol, bias in (("XLK", 0.01), ("XLP", -0.01)):
            features.append(
                {
                    "snapshot_time": timestamp,
                    "candidate_symbol": symbol,
                    "candidate_type": "sector_industry_etf",
                    "comparison_symbol": "SPY",
                    "rotation_pair_id": f"{symbol.lower()}_spy",
                    "relative_strength_return": bias + index / 1000,
                }
            )
            readiness = 0.7 if symbol == "XLK" else 0.2
            models.append(
                {
                    "available_time": timestamp,
                    "sector_or_industry_symbol": symbol,
                    "2_trend_stability_score": readiness,
                    "2_trend_certainty_score": 0.9,
                    "2_context_conditioned_stability_score": readiness,
                    "2_selection_readiness_score": readiness,
                    "2_sector_handoff_state": "selected" if symbol == "XLK" else "blocked",
                    "2_state_quality_score": 1.0,
                }
            )
    return features, models


class SectorContextEvaluationTests(unittest.TestCase):
    def test_builds_governance_artifacts_without_database_dependency(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        table_rows = artifacts.as_table_rows()

        self.assertEqual(len(table_rows["model_dataset_request"]), 1)
        self.assertEqual(len(table_rows["model_dataset_snapshot"]), 1)
        self.assertEqual(len(table_rows["model_dataset_split"]), 3)
        self.assertGreater(len(table_rows["model_eval_label"]), 0)
        self.assertGreater(len(table_rows["model_promotion_metric"]), 0)
        self.assertEqual(artifacts.dataset_request["required_feature_key"], "FEATURE_02_SECTOR_CONTEXT")
        self.assertEqual(artifacts.eval_run["model_id"], "model_02_sector_context")

    def test_future_labels_are_symbol_specific(self) -> None:
        features, models = _rows()
        artifacts = build_evaluation_artifacts(feature_rows=features, model_rows=models)
        label = next(label for label in artifacts.eval_labels if label["target_symbol"] == "XLK" and label["horizon"] == "1_step")

        self.assertEqual(label["available_time"], features[0]["snapshot_time"])
        self.assertEqual(label["label_time"], features[2]["snapshot_time"])
        self.assertEqual(label["label_value"], features[2]["relative_strength_return"])

    def test_future_labels_are_rotation_pair_specific_without_same_time_leakage(self) -> None:
        features, models = _rows()
        extra_features = []
        for row in features:
            if row["candidate_symbol"] == "XLK":
                clone = dict(row)
                clone["comparison_symbol"] = "QQQ"
                clone["rotation_pair_id"] = "xlk_qqq"
                clone["relative_strength_return"] = float(row["relative_strength_return"]) * 2
                extra_features.append(clone)
        artifacts = build_evaluation_artifacts(feature_rows=[*features, *extra_features], model_rows=models)

        self.assertTrue(artifacts.eval_labels)
        self.assertTrue(all(label["label_time"] > label["available_time"] for label in artifacts.eval_labels))
        xlk_labels = [label for label in artifacts.eval_labels if label["target_symbol"] == "XLK" and label["horizon"] == "1_step"]
        self.assertEqual(len({label["label_id"] for label in xlk_labels}), len(xlk_labels))
        self.assertEqual({label["label_payload_json"]["rotation_pair_id"] for label in xlk_labels}, {"xlk_spy", "xlk_qqq"})

    def test_summary_includes_sector_handoff_promotion_evidence(self) -> None:
        features, models = _rows()
        summary = summarize_artifacts(
            build_evaluation_artifacts(feature_rows=features, model_rows=models),
            thresholds={
                "minimum_feature_rows": 1,
                "minimum_model_rows": 1,
                "minimum_eval_labels": 1,
                "minimum_split_count": 1,
                "minimum_pair_count": 1,
                "minimum_coverage": 0,
                "minimum_factor_abs_pearson": 0,
                "minimum_baseline_improvement_abs": -1_000_000_000,
                "minimum_stability_sign_consistency": 0,
                "maximum_stability_correlation_range": 1_000_000_000,
                "maximum_leakage_violation_count": 0,
                "minimum_selected_count": 1,
                "minimum_selected_positive_rate": 0,
                "minimum_selected_average_label": -1,
            },
        )

        self.assertIn("handoff_summary", summary)
        self.assertIn("selected_count", summary["handoff_summary"])
        self.assertIn("threshold_results", summary)
        self.assertTrue(summary["promotion_evidence_ready"])

    def test_core_evaluator_has_no_database_connection_surface(self) -> None:
        text = (REPO_ROOT / "src" / "models" / "model_02_sector_context" / "evaluation.py").read_text(encoding="utf-8")
        for token in ["psycopg", "OPENCLAW_DATABASE_URL", "database-url", "connect(", "subprocess"]:
            self.assertNotIn(token, text)

    def test_database_reader_is_guarded_by_explicit_flag(self) -> None:
        text = EVALUATE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("--from-database", text)
        self.assertIn("READ ONLY: database rows were read", text)
        self.assertIn("DRY RUN ONLY: no database connection was opened", text)
        self.assertIn("if args.from_database:", text)

    def test_evaluation_script_fixture_summary(self) -> None:
        result = subprocess.run([sys.executable, str(EVALUATE_SCRIPT)], cwd=REPO_ROOT, env={"PYTHONPATH": "src"}, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.split("\nDRY RUN ONLY:", 1)[0])
        self.assertEqual(payload["write_policy"], "no_database_write")
        self.assertIn("handoff_summary", payload)

    def test_review_prompt_names_sector_context_gate(self) -> None:
        features, models = _rows()
        summary = summarize_artifacts(build_evaluation_artifacts(feature_rows=features, model_rows=models))
        prompt = build_sector_context_promotion_prompt(
            evaluation_summary=summary,
            config_version_row={"model_id": "model_02_sector_context"},
            promotion_candidate_row={"promotion_candidate_id": "candidate"},
        )

        self.assertIn("SectorContextModel", prompt)
        self.assertIn("sector handoff evidence", prompt)
        self.assertIn("ETF holdings", prompt)

    def test_review_script_local_fallback_defers_fixture_evidence(self) -> None:
        summary_path = Path("/tmp/sector_context_eval_summary_test.json")
        try:
            result = subprocess.run([sys.executable, str(EVALUATE_SCRIPT), "--output-json", str(summary_path)], cwd=REPO_ROOT, env={"PYTHONPATH": "src"}, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            review = subprocess.run([sys.executable, str(REVIEW_SCRIPT), "--evaluation-summary-json", str(summary_path), "--local-fallback-review"], cwd=REPO_ROOT, env={"PYTHONPATH": "src"}, text=True, capture_output=True, check=False)
            self.assertEqual(review.returncode, 0, review.stderr)
            payload = json.loads(review.stdout)
            self.assertFalse(payload["agent_review"]["can_promote"])
            self.assertEqual(payload["agent_review"]["decision_status"], "deferred")
        finally:
            summary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

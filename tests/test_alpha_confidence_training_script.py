from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "models" / "model_05_alpha_confidence" / "train_model_05_alpha_confidence.py"


class AlphaConfidenceTrainingScriptTests(unittest.TestCase):
    def test_builds_rejection_artifact_without_supervised_labels(self) -> None:
        script = _load_script()

        artifact = script.build_rejection_artifact(
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-05-01T00:00:00-05:00",
            all_horizons=True,
            from_database=True,
            generated_at_utc="2026-06-23T14:40:00Z",
        )

        self.assertEqual(artifact["contract_type"], "after_cost_alpha_training_rejected")
        self.assertEqual(artifact["training_summary"]["training_mode"], "supervised_fit_required")
        self.assertEqual(artifact["training_summary"]["sample_count"], 0)
        self.assertEqual(artifact["horizons"], ["10min", "1h", "1D", "1W"])
        self.assertFalse(artifact["safety"]["broker_execution_performed"])
        self.assertFalse(artifact["safety"]["model_activation_performed"])
        self.assertFalse(artifact["safety"]["provider_calls_performed"])

    def test_script_rejects_without_supervised_labels(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_path = Path(raw_tmp) / "after_cost_alpha_model_2016-01_2016-06.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--from-database",
                    "--all-horizons",
                    "--source-start",
                    "2016-01-01T00:00:00-05:00",
                    "--source-end",
                    "2016-05-01T00:00:00-05:00",
                    "--target-symbol",
                    "AAPL",
                    "--database-url",
                    "postgresql://invalid.invalid/openclaw",
                    "--output-json",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertFalse(output_path.exists())
            rejection_path = script_rejection_path(output_path)
            self.assertTrue(rejection_path.exists())
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(rejection["reason_code"], "after_cost_alpha_supervised_training_labels_missing")
            payload = json.loads(result.stderr)
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["reason_code"], "after_cost_alpha_supervised_training_labels_missing")

    def test_builds_supervised_model_artifact(self) -> None:
        script = _load_script()
        features = [
            {name: 0.1 for name in script.FEATURE_NAMES},
            {name: 0.9 for name in script.FEATURE_NAMES},
            {name: 0.2 for name in script.FEATURE_NAMES},
            {name: 0.8 for name in script.FEATURE_NAMES},
        ]
        labels = [0, 1, 0, 1]
        artifact = script.build_model_artifact(
            target_symbol="AAPL",
            source_start="2016-07-01T00:00:00-05:00",
            source_end="2016-11-01T00:00:00-05:00",
            horizons=["10min", "1h", "1D", "1W"],
            label_horizon="1D",
            cost_bps=10.0,
            features=features,
            labels=labels,
            label_summary={
                "sample_count": 4,
                "positive_count": 2,
                "negative_count": 2,
                "source_row_count": 4,
                "bar_row_count": 8,
                "mean_realized_after_cost_return": 0.01,
            },
        )

        self.assertEqual(artifact["contract_type"], "after_cost_alpha_model")
        self.assertEqual(artifact["model_type"], "fold_supervised_after_cost_alpha_logistic")
        self.assertEqual(artifact["target_symbol"], "AAPL")
        self.assertEqual(artifact["training_summary"]["training_mode"], "supervised_fit")
        self.assertEqual(artifact["training_summary"]["sample_count"], 4)
        self.assertEqual(artifact["score_model"]["model_family"], "logistic_regression")
        self.assertEqual(artifact["score_model"]["feature_names"], list(script.FEATURE_NAMES))


def _load_script():
    spec = importlib.util.spec_from_file_location("train_model_05_alpha_confidence", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def script_rejection_path(output_path: Path) -> Path:
    script = _load_script()
    return script.rejection_receipt_path(output_path)

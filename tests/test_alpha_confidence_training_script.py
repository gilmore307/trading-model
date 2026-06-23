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
    def test_builds_current_replay_entry_utility_bundle(self) -> None:
        script = _load_script()

        artifact = script.build_artifact(
            source_start="2016-01-01T00:00:00-05:00",
            source_end="2016-05-01T00:00:00-05:00",
            all_horizons=True,
            from_database=True,
            generated_at_utc="2026-06-23T14:40:00Z",
        )

        self.assertEqual(artifact["contract_type"], "current_replay_entry_utility_model_bundle")
        self.assertEqual(artifact["score_policy"], "derive_from_current_m02_m03_state")
        self.assertEqual(artifact["horizons"], ["10min", "1h", "1D", "1W"])
        self.assertFalse(artifact["safety"]["broker_execution_performed"])
        self.assertFalse(artifact["safety"]["model_activation_performed"])
        self.assertFalse(artifact["safety"]["provider_calls_performed"])

    def test_script_writes_manager_expected_output_json(self) -> None:
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
                    "--output-json",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(artifact["contract_type"], "current_replay_entry_utility_model_bundle")
            self.assertEqual(artifact["source_window"]["source_start"], "2016-01-01T00:00:00-05:00")


def _load_script():
    spec = importlib.util.spec_from_file_location("train_model_05_alpha_confidence", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

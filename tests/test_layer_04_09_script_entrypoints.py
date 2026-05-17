from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "model_04_event_failure_risk": "event_failure_risk",
    "model_05_alpha_confidence": "alpha_confidence",
    "model_06_position_projection": "position_projection",
    "model_07_underlying_action": "underlying_action",
    "model_08_option_expression": "option_expression",
    "model_09_event_risk_governor": "event_risk_governor",
}
LAYER_NUMBERS = {
    "model_04_event_failure_risk": 4,
    "model_05_alpha_confidence": 5,
    "model_06_position_projection": 6,
    "model_07_underlying_action": 7,
    "model_08_option_expression": 8,
    "model_09_event_risk_governor": 9,
}


class LayerFourNineScriptEntrypointTests(unittest.TestCase):
    def _load_script_module(self, script: Path):
        spec = importlib.util.spec_from_file_location(script.stem, script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generate_evaluate_review_scripts_support_help(self) -> None:
        for surface, slug in LAYERS.items():
            scripts = [
                f"scripts/models/{surface}/generate_{surface}.py",
                f"scripts/models/{surface}/evaluate_{surface}.py",
                f"scripts/models/{surface}/review_{slug}_promotion.py",
            ]
            for script in scripts:
                with self.subTest(script=script):
                    result = self._run([script, "--help"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("usage:", result.stdout)

    def test_model_09_sql_column_typing_uses_layer_09_prefix(self) -> None:
        generator = self._load_script_module(REPO_ROOT / "scripts/models/model_09_event_risk_governor/generate_model_09_event_risk_governor.py")

        self.assertEqual(generator._column_type("9_event_gap_risk_score_390min"), "DOUBLE PRECISION")
        self.assertEqual(generator._column_type("8_legacy_event_score"), "TEXT")

    def test_active_generator_column_type_prefixes_match_layer_numbers(self) -> None:
        for surface, layer_number in LAYER_NUMBERS.items():
            with self.subTest(surface=surface):
                generator = self._load_script_module(REPO_ROOT / f"scripts/models/{surface}/generate_{surface}.py")
                self.assertEqual(generator._column_type(f"{layer_number}_fixture_score"), "DOUBLE PRECISION")
                previous_layer = layer_number - 1
                self.assertEqual(generator._column_type(f"{previous_layer}_legacy_score"), "TEXT")

    def test_fixture_generate_evaluate_review_defers_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for surface, slug in LAYERS.items():
                with self.subTest(surface=surface):
                    rows_path = tmp_path / f"{surface}.jsonl"
                    eval_path = tmp_path / f"{surface}.eval.json"
                    review_path = tmp_path / f"{surface}.review.json"

                    generate = self._run([
                        f"scripts/models/{surface}/generate_{surface}.py",
                        "--output-jsonl",
                        str(rows_path),
                    ])
                    self.assertEqual(generate.returncode, 0, generate.stderr)
                    self.assertEqual(len(rows_path.read_text(encoding="utf-8").splitlines()), 1)

                    evaluate = self._run([
                        f"scripts/models/{surface}/evaluate_{surface}.py",
                        "--model-jsonl",
                        str(rows_path),
                        "--output-json",
                        str(eval_path),
                    ])
                    self.assertEqual(evaluate.returncode, 0, evaluate.stderr)
                    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
                    self.assertEqual(evaluation["summary"]["model_surface"], surface)
                    self.assertEqual(evaluation["summary"]["layer_number"], LAYER_NUMBERS[surface])
                    self.assertEqual(evaluation["summary"]["label_row_count"], 1)
                    self.assertTrue(evaluation["summary"]["leakage_check_passed"])
                    self.assertIn("fixture_or_local_evidence_must_defer", evaluation["summary"]["reason_codes"])

                    review = self._run([
                        f"scripts/models/{surface}/review_{slug}_promotion.py",
                        "--evaluation-summary-json",
                        str(eval_path),
                        "--output-json",
                        str(review_path),
                    ])
                    self.assertEqual(review.returncode, 0, review.stderr)
                    decision = json.loads(review_path.read_text(encoding="utf-8"))
                    self.assertEqual(decision["decision_status"], "deferred")
                    self.assertFalse(decision["activation_allowed"])


if __name__ == "__main__":
    unittest.main()

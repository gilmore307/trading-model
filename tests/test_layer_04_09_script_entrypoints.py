from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "model_04_event_failure_risk": "event_failure_risk",
    "model_09_event_risk_governor": "event_risk_governor",
    "model_05_alpha_confidence": "alpha_confidence",
    "model_06_position_projection": "position_projection",
    "model_07_underlying_action": "underlying_action",
    "model_08_option_expression": "option_expression",
}


class LayerFourNineScriptEntrypointTests(unittest.TestCase):
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

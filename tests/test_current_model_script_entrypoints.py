from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_SURFACES = {
    "model_01_background_context": ("background_context", 1),
    "model_02_target_state": ("target_state", 2),
    "model_03_event_state": ("event_state", 3),
    "model_04_unified_decision": ("unified_decision", 4),
    "model_05_option_expression": ("option_expression", 5),
    "model_06_residual_event_governance": ("residual_event_governance", 6),
}


class CurrentModelScriptEntrypointTests(unittest.TestCase):
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
        for surface, (slug, _) in MODEL_SURFACES.items():
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

    def test_active_generator_column_type_prefixes_match_model_numbers(self) -> None:
        for surface, (_, model_number) in MODEL_SURFACES.items():
            with self.subTest(surface=surface):
                generator = self._load_script_module(REPO_ROOT / f"scripts/models/{surface}/generate_{surface}.py")
                self.assertEqual(generator._column_type(f"{model_number}_fixture_score"), "DOUBLE PRECISION")
                other_model = 6 if model_number == 1 else model_number - 1
                self.assertEqual(generator._column_type(f"{other_model}_fixture_score"), "TEXT")


if __name__ == "__main__":
    unittest.main()

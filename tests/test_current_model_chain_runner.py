from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from model_governance.current_chain import CURRENT_CHAIN_MODELS, run_current_chain


REPO_ROOT = Path(__file__).resolve().parents[1]


class CurrentModelChainRunnerTests(unittest.TestCase):
    def test_current_chain_receipt_passes_local_fixture_handoffs(self) -> None:
        payload = run_current_chain()
        receipt = payload["receipt"]

        self.assertEqual(receipt["contract_type"], "current_model_chain_receipt")
        self.assertEqual(receipt["chain_status"], "passed")
        self.assertFalse(receipt["activation_allowed"])
        self.assertFalse(receipt["production_promotion_allowed"])
        self.assertEqual(receipt["model_order"], [model["model_surface"] for model in CURRENT_CHAIN_MODELS])
        self.assertTrue(all(check["passed"] for check in receipt["handoff_checks"]))
        handoff_names = {check["name"] for check in receipt["handoff_checks"]}
        self.assertIn("m01_to_m06_background_ref", handoff_names)
        self.assertIn("m03_to_m06_event_ref", handoff_names)
        self.assertTrue(receipt["retired_field_check_passed"])
        self.assertTrue(receipt["label_leakage_check_passed"])
        self.assertEqual(set(receipt["promotion_gate_states"].values()), {"deferred"})
        self.assertIn("unified_decision_vector_ref", receipt["resolved_outputs"])
        self.assertIn("event_risk_intervention_ref", receipt["resolved_outputs"])

    def test_current_chain_cli_emits_receipt_only(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/run_current_model_chain.py", "--receipt-only"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["contract_type"], "current_model_chain_receipt")
        self.assertEqual(receipt["chain_status"], "passed")
        self.assertFalse(receipt["activation_allowed"])

    def test_current_chain_cli_supports_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/run_current_model_chain.py", "--help"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()

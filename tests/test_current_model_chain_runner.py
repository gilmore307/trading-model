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
        self.assertIn("m01_to_m04_background_ref", handoff_names)
        self.assertIn("m03_to_m04_event_ref", handoff_names)
        self.assertIn("m04_to_m05_thesis_surface_ref", handoff_names)
        self.assertIn("m04_surface_to_m05_candidate_set_summary", handoff_names)
        self.assertTrue(receipt["retired_field_check_passed"])
        self.assertTrue(receipt["label_leakage_check_passed"])
        self.assertEqual(set(receipt["promotion_gate_states"].values()), {"deferred"})
        self.assertIn("thesis_distribution_surface_ref", receipt["resolved_outputs"])
        self.assertIn("unified_decision_vector_ref", receipt["resolved_outputs"])
        self.assertIn("expression_probability_surface_ref", receipt["resolved_outputs"])

    def test_current_chain_closes_return_surface_handoff(self) -> None:
        payload = run_current_chain(
            input_payload={
                "tradable_time_return_distribution_surface_summary": _surface_summary(),
            }
        )
        decision = payload["rows"]["model_04_unified_decision"][0]
        option = payload["rows"]["model_05_option_expression"][0]
        source_summary = decision["thesis_distribution_surface"]["source_tradable_time_return_distribution_surface"]
        candidate_summary = option["expression_candidate_set"]["source_thesis_distribution_surface_summary"]

        self.assertTrue(source_summary["available"])
        self.assertEqual(source_summary["contract_type"], "tradable_time_return_distribution_surface_summary")
        self.assertEqual(source_summary["target_grid_type"], "equal_step_tradable_time")
        self.assertEqual(source_summary["horizon_count"], 117)
        self.assertEqual(option["thesis_distribution_surface_ref"], decision["thesis_distribution_surface_ref"])
        self.assertTrue(candidate_summary["available"])
        self.assertEqual(candidate_summary["surface_ref"], decision["thesis_distribution_surface_ref"])
        self.assertTrue(all(check["passed"] for check in payload["receipt"]["handoff_checks"]))

    def test_current_chain_rejects_return_surface_symbol_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match routing_symbol"):
            run_current_chain(
                input_payload={
                    "routing_symbol": "MSFT",
                    "tradable_time_return_distribution_surface_summary": _surface_summary(),
                }
            )

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


def _surface_summary() -> dict:
    return {
        "contract_type": "tradable_time_return_distribution_surface_summary",
        "symbol": "AAPL",
        "source_table": "trading_data.model_01_market_regime_data_acquisition",
        "source_timeframe": "1Min",
        "anchor_minutes": 10,
        "target_grid": {
            "grid_type": "equal_step_tradable_time",
            "horizon_count": 117,
            "max_tau_trading_minutes": 1170,
        },
        "evaluation": {
            "mean_abs_coverage_error": 0.0068,
            "cdf_monotone_failures": 0,
        },
        "side_effects": {
            "provider_call_performed": False,
            "sql_mutation_performed": False,
            "model_activation_performed": False,
        },
    }


if __name__ == "__main__":
    unittest.main()

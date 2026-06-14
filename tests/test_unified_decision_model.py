from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.model_04_unified_decision import generate_rows
from models.model_04_unified_decision.evaluation import assert_no_label_leakage, build_unified_decision_labels


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_OUTPUT_FIELDS = {
    "alpha_confidence_vector",
    "dynamic_risk_policy_state",
    "position_projection_vector",
    "underlying_action_vector",
    "underlying_action_plan",
}


class UnifiedDecisionModelTests(unittest.TestCase):
    def test_generates_single_current_vector_with_structured_heads(self) -> None:
        output = generate_rows([_base_row()])[0]
        vector = output["unified_decision_vector"]
        intent = output["direct_underlying_intent"]

        self.assertEqual(output["model_id"], "unified_decision_model")
        self.assertEqual(output["model_step"], "M04")
        self.assertIn("unified_decision_vector_ref", output)
        self.assertGreater(vector["4_after_cost_edge_score_1W"], 0.5)
        self.assertGreater(vector["4_risk_budget_score_1W"], 0.0)
        self.assertGreater(vector["4_target_exposure_score_1W"], 0.0)
        self.assertGreater(vector["4_materiality_adjusted_action_score_1W"], 0.0)
        self.assertEqual(vector["4_resolved_underlying_action_type"], "open_long")
        self.assertEqual(
            vector["4_resolved_materiality_adjusted_action_score"],
            vector["4_materiality_adjusted_action_score_1W"],
        )
        self.assertEqual(intent["handoff_to_model_05"]["underlying_path_direction"], "bullish")
        self.assertEqual(
            intent["materiality_adjusted_action_score"],
            vector["4_resolved_materiality_adjusted_action_score"],
        )
        self.assert_no_retired_outputs(output)
        assert_no_label_leakage(output)

    def test_pending_adjusted_exposure_prevents_duplicate_increase(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    current_underlying_position_state={"current_underlying_exposure_score": 0.10},
                    pending_underlying_order_state={
                        "pending_underlying_exposure_score": 0.114377,
                        "pending_fill_probability_estimate": 1.0,
                    },
                )
            ]
        )[0]

        self.assertEqual(output["direct_underlying_intent"]["current_effective_exposure_score"], 0.214377)
        self.assertEqual(output["4_resolved_underlying_action_type"], "maintain")
        self.assertIn("position_gap_below_materiality", output["4_resolved_reason_codes"])

    def test_horizon_resolution_uses_materiality_adjusted_action_not_raw_intensity(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    policy_gate_state={"direct_underlying_action_allowed": True},
                    target_context_state={
                        "2_target_direction_score_1D": 1.0,
                        "2_target_trend_quality_score_1D": 0.45,
                        "2_target_path_stability_score_1D": 0.35,
                        "2_target_noise_score_1D": 0.35,
                        "2_target_transition_risk_score_1D": 0.35,
                        "2_context_support_quality_score_1D": 0.35,
                        "2_tradability_score_1D": 0.95,
                        "2_target_direction_score_1W": 0.55,
                        "2_target_trend_quality_score_1W": 0.78,
                        "2_target_path_stability_score_1W": 0.82,
                        "2_target_noise_score_1W": 0.12,
                        "2_target_transition_risk_score_1W": 0.08,
                        "2_context_support_quality_score_1W": 0.84,
                        "2_tradability_score_1W": 0.90,
                    },
                )
            ]
        )[0]

        vector = output["unified_decision_vector"]
        self.assertGreater(vector["4_trade_intensity_score_1D"], vector["4_trade_intensity_score_1W"])
        self.assertGreater(
            vector["4_materiality_adjusted_action_score_1W"],
            vector["4_materiality_adjusted_action_score_1D"],
        )
        self.assertEqual(vector["4_resolved_decision_horizon"], "1W")

    def test_hard_gate_blocks_new_exposure(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    underlying_quote_state={"reference_price": 100.0, "bid_price": 99.9, "ask_price": 100.1, "halt_status": "halted"}
                )
            ]
        )[0]

        self.assertEqual(output["4_resolved_underlying_action_type"], "no_trade")
        self.assertEqual(output["4_action_eligibility_score_1W"], 0.0)
        self.assertIn("halt_status_not_active", output["4_resolved_reason_codes"])

    def test_bearish_flat_without_short_borrow_does_not_choose_option_contract(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    target_context_state={
                        "2_target_direction_score_1W": -0.80,
                        "2_target_trend_quality_score_1W": 0.75,
                        "2_target_path_stability_score_1W": 0.80,
                        "2_context_support_quality_score_1W": 0.78,
                        "2_tradability_score_1W": 0.85,
                    },
                    underlying_borrow_state={"short_borrow_status": "unavailable"},
                )
            ]
        )[0]

        self.assertEqual(output["4_resolved_underlying_action_type"], "bearish_underlying_path_but_no_short_allowed")
        self.assertEqual(output["4_resolved_action_side"], "none")
        self.assert_no_retired_outputs(output)

    def test_labels_are_offline_and_join_by_unified_decision_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_unified_decision_labels(
            [output],
            [
                {
                    "unified_decision_vector_ref": output["unified_decision_vector_ref"],
                    "realized_decision_utility": 0.12,
                    "realized_max_drawdown": -0.03,
                    "no_trade_would_have_been_better": False,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertAlmostEqual(labels[0]["realized_decision_utility"], 0.12)
        self.assertNotIn("realized_decision_utility", output)

    def test_current_script_fixture_emits_unified_decision_rows(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 1)
        self.assertIn("unified_decision_vector", rows[0])
        self.assertNotIn("alpha_confidence_vector", rows[0])

    def test_current_script_column_type_uses_model_04_prefix(self) -> None:
        script = _load_generator_script()

        self.assertEqual(script._column_type("4_after_cost_edge_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("4_resolved_underlying_action_type"), "TEXT")
        self.assertEqual(script._column_type("5_after_cost_edge_score_1W"), "TEXT")

    def test_database_input_rows_map_m03_and_event_context(self) -> None:
        script = _load_generator_script()
        source_rows = [
            {
                "available_time": "2016-01-04T09:35:00-05:00",
                "tradeable_time": "2016-01-04T09:36:00-05:00",
                "target_candidate_id": "anon_aapl",
                "target_context_state_ref": "tcsv_1",
                "event_failure_risk_vector_ref": "efrv_1",
                "underlying_symbol": "AAPL",
                "underlying_reference_price": 102.5,
                "last_bid": 102.45,
                "last_ask": 102.55,
                "spread_bps": 9.8,
                "dollar_volume": 1_000_000.0,
                "3_state_quality_score": 0.91,
                "target_context_state": {
                    "3_target_direction_score_1W": 0.6,
                    "3_target_trend_quality_score_1W": 0.7,
                },
                "event_state_vector": {"4_event_entry_block_pressure_score_1W": 0.2},
            }
        ]

        rows = script._model_04_input_rows(source_rows)

        self.assertEqual(rows[0]["target_candidate_id"], "anon_aapl")
        self.assertEqual(rows[0]["target_context_state"]["3_target_direction_score_1W"], 0.6)
        self.assertEqual(rows[0]["event_state_vector"]["4_event_entry_block_pressure_score_1W"], 0.2)
        self.assertEqual(rows[0]["underlying_quote_state"]["reference_price"], 102.5)
        self.assertEqual(rows[0]["underlying_liquidity_state"]["spread_bps"], 9.8)

    def test_current_generate_evaluate_review_scripts_support_help(self) -> None:
        scripts = [
            "scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py",
            "scripts/models/model_04_unified_decision/evaluate_model_04_unified_decision.py",
            "scripts/models/model_04_unified_decision/review_unified_decision_promotion.py",
        ]

        for script in scripts:
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, script, "--help"],
                    cwd=REPO_ROOT,
                    env={"PYTHONPATH": "src"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_current_evaluate_and_review_scripts_defer_fixture_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            review_path = Path(tmp) / "review.json"
            eval_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_04_unified_decision/evaluate_model_04_unified_decision.py",
                    "--output-json",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(eval_result.returncode, 0, eval_result.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["summary"]["model_surface"], "model_04_unified_decision")
            self.assertEqual(summary["summary"]["promotion_gate_state"], "deferred")

            review_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_04_unified_decision/review_unified_decision_promotion.py",
                    "--evaluation-summary-json",
                    str(summary_path),
                    "--output-json",
                    str(review_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(review_result.returncode, 0, review_result.stderr)
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["decision_status"], "deferred")
            self.assertFalse(review["activation_allowed"])

    def assert_no_retired_outputs(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key), RETIRED_OUTPUT_FIELDS)
                self.assert_no_retired_outputs(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_retired_outputs(nested)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "background_context_state_ref": "bcs_fixture",
        "target_context_state_ref": "tcs_fixture",
        "event_state_vector_ref": "esv_fixture",
        "background_context_state": {
            "1_market_risk_stress_score": 0.20,
            "1_market_liquidity_support_score": 0.85,
        },
        "target_context_state": {
            "2_target_direction_score_1W": 0.80,
            "2_target_trend_quality_score_1W": 0.76,
            "2_target_path_stability_score_1W": 0.82,
            "2_target_noise_score_1W": 0.18,
            "2_target_transition_risk_score_1W": 0.14,
            "2_context_support_quality_score_1W": 0.80,
            "2_tradability_score_1W": 0.86,
        },
        "event_state_vector": {
            "3_event_entry_block_pressure_score_1W": 0.10,
            "3_event_exposure_cap_pressure_score_1W": 0.05,
            "3_event_strategy_disable_pressure_score_1W": 0.00,
            "3_event_path_risk_score_1W": 0.12,
            "3_event_uncertainty_score_1W": 0.15,
            "3_event_applicability_confidence_score_1W": 0.50,
        },
        "quality_calibration_state": {
            "data_quality_score": 0.90,
            "walk_forward_reliability_score": 0.82,
            "out_of_distribution_score": 0.08,
        },
        "portfolio_exposure_state": {
            "gross_exposure_capacity_score": 0.85,
            "correlation_concentration_score": 0.20,
        },
        "account_capacity_state": {"cash_capacity_score": 0.78, "drawdown_pressure_score": 0.12},
        "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
        "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
        "cost_friction_state": {
            "spread_cost_estimate": 0.001,
            "slippage_cost_estimate": 0.001,
            "fee_cost_estimate": 0.0005,
            "turnover_cost_estimate": 0.001,
        },
        "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
        "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50_000_000, "liquidity_score": 0.95},
        "underlying_borrow_state": {"short_borrow_status": "available"},
        "risk_budget_state": {"risk_budget_available_score": 0.95},
        "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
    }
    row.update(overrides)
    return row


def _load_generator_script():
    script = REPO_ROOT / "scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py"
    spec = importlib.util.spec_from_file_location(script.stem, script)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load M04 generator script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()

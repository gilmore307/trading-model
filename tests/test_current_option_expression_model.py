from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.model_05_option_expression import generate_rows
from models.model_05_option_expression.contract import EVENT_STATE_CONSUMED_FIELDS
from models.model_05_option_expression.evaluation import assert_no_label_leakage, build_option_expression_labels


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_INPUT_OUTPUT_FIELDS = {
    "underlying_action_plan",
    "underlying_action_vector",
    "underlying_action_plan_ref",
}


class CurrentOptionExpressionModelTests(unittest.TestCase):
    def test_contract_consumes_event_state_option_impact_without_owning_event_taxonomy(self) -> None:
        self.assertIn("3_event_option_price_impact_score_<horizon>", EVENT_STATE_CONSUMED_FIELDS)
        self.assertIn("3_event_volatility_surface_impact_score_<horizon>", EVENT_STATE_CONSUMED_FIELDS)
        self.assertIn("3_event_expiry_gamma_flow_impact_score_<horizon>", EVENT_STATE_CONSUMED_FIELDS)

    def test_direct_underlying_intent_selects_long_call(self) -> None:
        output = generate_rows([_base_row()])[0]
        plan = output["option_expression_plan"]

        self.assertEqual(output["model_id"], "option_expression_model")
        self.assertEqual(output["model_step"], "M05")
        self.assertEqual(output["unified_decision_vector_ref"], "udv_fixture")
        self.assertEqual(output["5_resolved_expression_type"], "long_call")
        self.assertEqual(output["5_resolved_option_right"], "call")
        self.assertEqual(output["5_resolved_selected_contract_ref"], "AAPL_CALL_GOOD")
        self.assertGreater(output["5_option_expression_confidence_score_1W"], 0.0)
        self.assertEqual(plan["underlying_thesis_ref"], "udv_fixture")
        self.assertEqual(plan["underlying_path_assumptions"]["underlying_path_direction"], "bullish")
        assert_no_label_leakage(output)
        self.assert_no_retired_fields(output)

    def test_no_trade_intent_keeps_surface_diagnostics_without_overlay(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    direct_underlying_intent={
                        "underlying_action_type": "no_trade",
                        "action_side": "none",
                        "dominant_horizon": "1W",
                        "handoff_to_model_05": _handoff(),
                    }
                )
            ]
        )[0]

        self.assertEqual(output["5_resolved_expression_type"], "no_option_expression")
        self.assertEqual(output["5_resolved_option_surface_status"], "optionable_chain_available")
        self.assertIn("underlying_action_no_trade", output["5_resolved_no_option_reason_codes"])
        self.assertGreater(output["option_expression_plan"]["diagnostics"]["candidate_count_before_filter"], 0)

    def test_bearish_no_direct_short_intent_selects_long_put(self) -> None:
        row = _base_row(
            direct_underlying_intent={
                "underlying_action_type": "bearish_underlying_path_but_no_short_allowed",
                "action_side": "bearish_no_direct_short",
                "dominant_horizon": "1W",
                "handoff_to_model_05": {
                    **_handoff(),
                    "underlying_path_direction": "bearish",
                    "expected_favorable_move_pct": 0.045,
                    "expected_adverse_move_pct": -0.018,
                },
            }
        )
        output = generate_rows([row])[0]

        self.assertEqual(output["5_resolved_expression_type"], "long_put")
        self.assertEqual(output["5_resolved_option_right"], "put")
        self.assertEqual(output["5_resolved_selected_contract_ref"], "AAPL_PUT_GOOD")
        self.assertLess(output["5_option_expression_direction_score_1W"], 0.0)

    def test_option_expression_policy_block_can_fall_back_to_underlying_only(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    option_expression_policy={
                        "option_expression_allowed": False,
                        "allow_underlying_only_expression": True,
                    }
                )
            ]
        )[0]

        self.assertEqual(output["5_resolved_expression_type"], "underlying_only_expression")
        self.assertEqual(output["5_resolved_option_right"], "none")
        self.assertIn("option_expression_policy_blocked", output["5_resolved_reason_codes"])

    def test_non_optionable_underlying_uses_direct_underlying_expression_without_chain(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    option_expression_policy={
                        "option_surface_status": "non_optionable_underlying",
                        "option_expression_allowed": False,
                        "allow_underlying_only_expression": True,
                    },
                    option_contract_candidates=[],
                )
            ]
        )[0]

        self.assertEqual(output["5_resolved_expression_type"], "underlying_only_expression")
        self.assertEqual(output["5_resolved_option_right"], "none")
        self.assertEqual(output["5_resolved_option_surface_status"], "non_optionable_underlying")
        self.assertIsNone(output["5_resolved_selected_contract_ref"])
        self.assertIn("non_optionable_underlying", output["5_resolved_reason_codes"])
        self.assertIn("underlying_only_expression_selected", output["5_resolved_reason_codes"])
        self.assertEqual(output["option_expression_plan"]["diagnostics"]["candidate_count_before_filter"], 0)

    def test_labels_are_offline_and_join_by_plan_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_option_expression_labels(
            [output],
            [
                {
                    "option_expression_plan_ref": output["option_expression_plan_ref"],
                    "realized_option_return_1W": 0.42,
                    "target_premium_hit_before_stop_label_1W": True,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0]["target_premium_hit_before_stop_label_1W"])
        self.assertNotIn("realized_option_return_1W", output)

    def test_current_script_fixture_emits_model_05_rows(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/model_05_option_expression/generate_model_05_option_expression.py"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model_step"], "M05")
        self.assertIn("5_resolved_expression_type", rows[0])
        self.assertNotIn("underlying_action_plan_ref", rows[0])

    def test_current_generate_evaluate_review_scripts_support_help(self) -> None:
        scripts = [
            "scripts/models/model_05_option_expression/generate_model_05_option_expression.py",
            "scripts/models/model_05_option_expression/evaluate_model_05_option_expression.py",
            "scripts/models/model_05_option_expression/review_option_expression_promotion.py",
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
                    "scripts/models/model_05_option_expression/evaluate_model_05_option_expression.py",
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
            self.assertEqual(summary["summary"]["model_surface"], "model_05_option_expression")
            self.assertEqual(summary["summary"]["promotion_gate_state"], "deferred")

            review_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_05_option_expression/review_option_expression_promotion.py",
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

    def test_current_script_column_type_uses_model_05_prefix(self) -> None:
        script = _load_generator_script()

        self.assertEqual(script._column_type("5_option_expression_confidence_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("5_resolved_expression_type"), "TEXT")
        self.assertEqual(script._column_type("4_option_expression_confidence_score_1W"), "TEXT")

    def test_database_generation_refreshes_manager_task_progress(self) -> None:
        script = _load_generator_script()

        with tempfile.TemporaryDirectory() as tmpdir:
            previous_env = {
                key: os.environ.get(key)
                for key in (
                    "TRADING_MANAGER_TASK_PROGRESS_ROOT",
                    "TRADING_MANAGER_TASK_PROGRESS_WORKER_ID",
                    "TRADING_MANAGER_TASK_PROGRESS_TASK_UID",
                    "TRADING_MANAGER_TASK_PROGRESS_STAGE_ID",
                    "TRADING_MODEL_DATASET_SPLIT_NAME",
                    "TRADING_MODEL_DATASET_SPLIT_POLICY",
                )
            }
            try:
                os.environ.update(
                    {
                        "TRADING_MANAGER_TASK_PROGRESS_ROOT": tmpdir,
                        "TRADING_MANAGER_TASK_PROGRESS_WORKER_ID": "model_worker_1",
                        "TRADING_MANAGER_TASK_PROGRESS_TASK_UID": "2016-01..2017-06:model_05_option_expression.model_generation.train",
                        "TRADING_MANAGER_TASK_PROGRESS_STAGE_ID": "model_05_option_expression.model_generation.train",
                        "TRADING_MODEL_DATASET_SPLIT_NAME": "train",
                        "TRADING_MODEL_DATASET_SPLIT_POLICY": "chronological_cumulative_walk_forward_12_3_3",
                    }
                )

                script._write_stage_progress(
                    node_id="fetch_database_input_rows",
                    node_label="Fetch database input rows",
                    current_activity="Generating M05 option-expression rows from database inputs",
                )

                progress = json.loads((Path(tmpdir) / "model_worker_1.json").read_text(encoding="utf-8"))
                self.assertEqual(progress["contract_type"], "manager_worker_task_progress")
                self.assertEqual(progress["status"], "running")
                self.assertEqual(progress["stage_id"], "model_05_option_expression.model_generation.train")
                self.assertIsNone(progress["processed_count"])
                self.assertEqual(progress["nodes"][0]["node_id"], "fetch_database_input_rows")
                self.assertEqual(progress["extra"]["dataset_split"]["split_name"], "train")
                self.assertEqual(progress["extra"]["source"], "model_05_option_expression_database_generator")

                script._write_stage_progress(
                    node_id="generate_model_rows",
                    node_label="Generate model rows",
                    current_activity="Generated 7/12 M05 option-expression rows",
                    processed_count=7,
                    expected_count=12,
                )
                progress = json.loads((Path(tmpdir) / "model_worker_1.json").read_text(encoding="utf-8"))
                self.assertEqual(progress["processed_count"], 7)
                self.assertEqual(progress["expected_count"], 12)
                self.assertEqual(progress["unit_label"], "rows")
                self.assertEqual(progress["nodes"][0]["processed_count"], 7)
                self.assertEqual(progress["nodes"][0]["expected_count"], 12)
            finally:
                for key, value in previous_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def assert_no_retired_fields(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key), RETIRED_INPUT_OUTPUT_FIELDS)
                self.assert_no_retired_fields(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_retired_fields(nested)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "unified_decision_vector_ref": "udv_fixture",
        "option_chain_snapshot_ref": "chain_snapshot_fixture",
        "option_quote_available_time": "2026-05-07T10:30:05-04:00",
        "underlying_quote_snapshot_ref": "underlying_quote_fixture",
        "underlying_reference_price": 100.25,
        "direct_underlying_intent": {
            "underlying_action_type": "open_long",
            "action_side": "long",
            "dominant_horizon": "1W",
            "handoff_to_model_05": _handoff(),
        },
        "background_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85},
        "event_state_vector": {"3_event_path_risk_score_1W": 0.20, "3_event_uncertainty_score_1W": 0.15},
        "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
        "option_contract_candidates": [
            _call_candidate(),
            {
                "contract_ref": "AAPL_PUT_GOOD",
                "quote_snapshot_ref": "qs_put_good",
                "quote_age_seconds": 15,
                "strike": 98,
                "contract_multiplier": 100,
                "right": "put",
                "expiration": "2026-06-06",
                "dte": 30,
                "delta": -0.50,
                "gamma": 0.04,
                "theta": -0.08,
                "vega": 0.12,
                "iv": 0.34,
                "iv_rank": 0.48,
                "bid": 2.30,
                "ask": 2.45,
                "volume": 900,
                "open_interest": 4200,
            },
        ],
    }
    row.update(overrides)
    return row


def _call_candidate() -> dict[str, object]:
    return {
        "contract_ref": "AAPL_CALL_GOOD",
        "quote_snapshot_ref": "qs_call_good",
        "quote_available_time": "2026-05-07T10:30:05-04:00",
        "quote_age_seconds": 12,
        "strike": 102,
        "moneyness": 1.02,
        "contract_multiplier": 100,
        "exercise_style": "american",
        "settlement_type": "physical",
        "is_weekly": True,
        "is_monthly": False,
        "is_adjusted_contract": False,
        "last_trade_time": "2026-05-07T10:29:58-04:00",
        "right": "call",
        "expiration": "2026-06-06",
        "dte": 30,
        "delta": 0.52,
        "gamma": 0.04,
        "theta": -0.08,
        "vega": 0.12,
        "iv": 0.32,
        "iv_rank": 0.45,
        "bid": 2.40,
        "ask": 2.55,
        "bid_size": 30,
        "ask_size": 25,
        "volume": 1200,
        "open_interest": 6500,
        "intrinsic_value": 2.0,
        "extrinsic_value": 0.475,
        "breakeven_price": 104.475,
        "theoretical_value": 2.49,
    }


def _handoff() -> dict[str, object]:
    return {
        "underlying_path_direction": "bullish",
        "expected_entry_price": 100.0,
        "expected_target_price": 105.0,
        "target_price_low": 103.0,
        "target_price_high": 106.0,
        "stop_loss_price": 98.0,
        "thesis_invalidation_price": 97.5,
        "expected_holding_time_minutes": 10080,
        "path_quality_score": 0.82,
        "reversal_risk_score": 0.18,
        "drawdown_risk_score": 0.22,
        "expected_favorable_move_pct": 0.05,
        "expected_adverse_move_pct": -0.02,
        "entry_price_assumption": "limit_or_pullback",
        "underlying_action_confidence_score": 0.78,
    }


def _load_generator_script():
    script = REPO_ROOT / "scripts/models/model_05_option_expression/generate_model_05_option_expression.py"
    spec = importlib.util.spec_from_file_location(script.stem, script)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load M05 generator script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()

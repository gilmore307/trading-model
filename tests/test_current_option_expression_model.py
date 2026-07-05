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
from models.model_05_option_expression.contract import CANDIDATE_SET_OUTPUT, EVENT_STATE_CONSUMED_FIELDS
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
        self.assertEqual(output["thesis_distribution_surface_ref"], "tds_fixture")
        self.assertEqual(output["5_resolved_expression_type"], "long_call")
        self.assertEqual(output["5_resolved_option_right"], "call")
        self.assertEqual(output["5_resolved_selected_contract_ref"], "AAPL_CALL_GOOD")
        self.assertGreater(output["5_option_expression_confidence_score_1W"], 0.0)
        self.assertEqual(plan["underlying_thesis_ref"], "udv_fixture")
        self.assertEqual(plan["underlying_path_assumptions"]["underlying_path_direction"], "bullish")
        candidate_set = output[CANDIDATE_SET_OUTPUT]
        self.assertEqual(candidate_set["source_m04_decision_ref"], "udv_fixture")
        self.assertEqual(candidate_set["source_thesis_distribution_surface_ref"], "tds_fixture")
        self.assertTrue(candidate_set["source_thesis_distribution_surface_summary"]["available"])
        self.assertEqual(candidate_set["source_thesis_distribution_surface_summary"]["resolved_horizon"], "1W")
        self.assertFalse(candidate_set["selector_result"]["production_behavior_changed"])
        self.assertEqual(candidate_set["selector_result"]["selected_expression_type"], "long_call")
        self.assertEqual(plan["diagnostics"]["expression_candidate_set_ref"], candidate_set["candidate_set_ref"])
        self.assertEqual(plan["diagnostics"]["expression_candidate_count"], candidate_set["candidate_count"])
        candidates = candidate_set["candidate_vectors"]
        self.assertEqual({candidate["expression_type"] for candidate in candidates}, {"underlying_equity", "option_contract"})
        self.assertEqual(_selected_candidate(candidate_set)["instrument_ref"], "AAPL_CALL_GOOD")
        self.assertEqual(_selected_candidate(candidate_set)["expression_type"], "option_contract")
        self.assertEqual(_selected_candidate(candidate_set)["source_thesis_distribution_surface_ref"], "tds_fixture")
        self.assertTrue(_selected_candidate(candidate_set)["components"]["inherited_thesis_distribution_surface"]["available"])
        self.assertIn("underlying_equity_proxy", {candidate["instrument_ref"] for candidate in candidates})
        rejected_put = next(candidate for candidate in candidates if candidate["instrument_ref"] == "AAPL_PUT_GOOD")
        self.assertEqual(rejected_put["eligibility_status"], "rejected")
        self.assertIn("option_right_mismatch", rejected_put["rejection_reasons"])
        self.assertEqual(len(_candidate_vector_key_sets(candidate_set)), 1)
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

    def test_no_option_expression_is_scored_against_eligible_contracts(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    option_contract_candidates=[
                        {
                            **_call_candidate(),
                            "contract_ref": "AAPL_CALL_FRAGILE",
                            "dte": 45,
                            "delta": 0.35,
                            "bid": 1.00,
                            "ask": 1.18,
                            "volume": 0,
                            "open_interest": 0,
                            "iv_rank": 0.74,
                        }
                    ],
                )
            ]
        )[0]
        diagnostics = output["option_expression_plan"]["diagnostics"]

        self.assertEqual(output["5_resolved_expression_type"], "no_option_expression")
        self.assertGreater(output["5_option_expression_direction_score_1W"], 0.0)
        self.assertEqual(diagnostics["candidate_count_after_filter"], 1)
        self.assertEqual(diagnostics["no_option_proxy_expression_type"], "underlying_equity")
        self.assertGreater(diagnostics["no_option_candidate_score"], diagnostics["expression_selector"]["best_contract_score"])
        self.assertEqual(diagnostics["expression_selector"]["selection_reason"], "no_option_won_policy_adjusted_score")
        self.assertIn("no_option_won_policy_adjusted_score", output["5_resolved_reason_codes"])
        candidate_set = output[CANDIDATE_SET_OUTPUT]
        selected = _selected_candidate(candidate_set)
        self.assertEqual(selected["expression_type"], "underlying_equity")
        self.assertEqual(selected["instrument_ref"], "underlying_equity_proxy")
        self.assertEqual(selected["selector_utility"], selected["comparable_vector"]["selector_utility"])
        self.assertEqual(len(_candidate_vector_key_sets(candidate_set)), 1)

    def test_no_option_comparison_does_not_expand_dte_policy(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    option_contract_candidates=[
                        {
                            **_call_candidate(),
                            "contract_ref": "AAPL_CALL_OUTSIDE_DTE",
                            "dte": 90,
                        }
                    ]
                )
            ]
        )[0]
        diagnostics = output["option_expression_plan"]["diagnostics"]

        self.assertEqual(output["5_resolved_expression_type"], "no_option_expression")
        self.assertEqual(diagnostics["candidate_count_after_filter"], 0)
        self.assertEqual(diagnostics["expression_selector"]["selection_reason"], "no_option_won_no_eligible_contract")
        self.assertEqual(diagnostics["candidate_filter_reason_counts"]["dte_outside_policy_range"], 1)
        candidate_set = output[CANDIDATE_SET_OUTPUT]
        selected = _selected_candidate(candidate_set)
        self.assertEqual(selected["expression_type"], "underlying_equity")
        rejected = next(candidate for candidate in candidate_set["candidate_vectors"] if candidate["instrument_ref"] == "AAPL_CALL_OUTSIDE_DTE")
        self.assertEqual(rejected["eligibility_status"], "rejected")
        self.assertIn("dte_outside_policy_range", rejected["rejection_reasons"])
        self.assertEqual(len(_candidate_vector_key_sets(candidate_set)), 1)

    def test_bearish_no_direct_short_intent_selects_long_put(self) -> None:
        row = _base_row(
            direct_underlying_intent={
                "underlying_action_type": "bearish_underlying_path_but_no_short_allowed",
                "action_side": "none",
                "direction_thesis": "bearish",
                "trade_eligibility_status": "blocked_by_direct_short_policy",
                "dominant_horizon": "1W",
                "handoff_to_model_05": {
                    **_handoff(),
                    "underlying_path_direction": "bearish",
                    "direction_thesis": "bearish",
                    "trade_eligibility_status": "blocked_by_direct_short_policy",
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
        selected = _selected_candidate(output[CANDIDATE_SET_OUTPUT])
        self.assertEqual(selected["expression_type"], "underlying_equity")

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
        self.assertIn(CANDIDATE_SET_OUTPUT, rows[0])
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

        self.assertEqual(script._column_type(CANDIDATE_SET_OUTPUT), "JSONB")
        self.assertEqual(script._column_type("5_option_expression_confidence_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("5_resolved_expression_type"), "TEXT")
        self.assertEqual(script._column_type("4_option_expression_confidence_score_1W"), "TEXT")

    def test_database_generation_default_batch_is_candidate_vector_safe(self) -> None:
        script = _load_generator_script()

        self.assertLessEqual(script.DATABASE_BATCH_SIZE, 500)

    def test_database_fetch_projects_only_m05_input_columns(self) -> None:
        script = _load_generator_script()
        cursor = _FakeCursor(
            fetchone_rows=[{"table_ref": "trading_model.model_04_unified_decision_explainability"}],
            fetchall_rows=[],
        )

        script._fetch_model_04_rows(cursor, source_start="2016-01-01T00:00:00-05:00", source_end="2017-01-01T00:00:00-05:00")

        select_sql = cursor.executed_sql[1]
        self.assertIn('u."available_time"', select_sql)
        self.assertIn('u."tradeable_time"', select_sql)
        self.assertIn('u."target_candidate_id"', select_sql)
        self.assertIn('u."unified_decision_vector_ref"', select_sql)
        self.assertIn('e."direct_underlying_intent"', select_sql)
        self.assertNotIn("u.*", select_sql)
        self.assertNotIn('e."unified_decision_vector"', select_sql)

    def test_database_option_candidate_fetch_accepts_source_cache_feature_rows(self) -> None:
        script = _load_generator_script()
        cursor = _FakeCursor(
            fetchone_rows=[{"table_ref": "trading_data.model_05_option_expression_feature_generation"}],
            fetchall_rows=[],
        )

        script._fetch_option_candidate_rows(cursor, source_start="2016-01-01T00:00:00-05:00", source_end="2016-02-01T00:00:00-05:00")

        select_sql = cursor.executed_sql[1]
        self.assertIn('lower(coalesce(f."snapshot_type", \'\')) = ANY(%s)', select_sql)
        self.assertNotIn("= 'entry'", select_sql)
        self.assertIn("source_cache", script.OPTION_CANDIDATE_SNAPSHOT_TYPES)

    def test_candidate_index_keeps_source_cache_option_surface_rows(self) -> None:
        script = _load_generator_script()

        index = script._candidate_index(
            [
                {
                    "underlying": "AAPL",
                    "snapshot_time": "2016-01-04T09:30:00-05:00",
                    "snapshot_type": "source_cache",
                    "option_symbol": "AAPL_2016-01-08_C_100",
                    "feature_payload_json": {"option_right": "call", "dte": 4, "mid_price": 1.25},
                    "feature_quality_diagnostics": {"has_required_fields": True},
                }
            ]
        )

        candidates = index[("AAPL", "2016-01-04T09:30:00-05:00")]
        self.assertEqual(candidates[0]["contract_ref"], "AAPL_2016-01-08_C_100")
        self.assertEqual(candidates[0]["option_right"], "call")

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


def _selected_candidate(candidate_set: dict[str, object]) -> dict[str, object]:
    candidates = candidate_set["candidate_vectors"]
    if not isinstance(candidates, list):
        raise AssertionError("candidate_vectors must be a list")
    selected = [candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("selected_by_compatibility_selector")]
    if len(selected) != 1:
        raise AssertionError(f"expected one selected expression candidate, got {len(selected)}")
    return selected[0]


def _candidate_vector_key_sets(candidate_set: dict[str, object]) -> set[frozenset[str]]:
    candidates = candidate_set["candidate_vectors"]
    if not isinstance(candidates, list):
        raise AssertionError("candidate_vectors must be a list")
    return {
        frozenset(candidate["comparable_vector"].keys())
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("comparable_vector"), dict)
    }


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "unified_decision_vector_ref": "udv_fixture",
        "thesis_distribution_surface_ref": "tds_fixture",
        "thesis_distribution_surface": _thesis_surface(),
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


def _thesis_surface() -> dict[str, object]:
    return {
        "surface_ref": "tds_fixture",
        "schema_ref": "thesis_distribution_surface",
        "source_model": "model_04_unified_decision",
        "source_unified_decision_vector_ref": "udv_fixture",
        "surface_type": "discrete_horizon_return_distribution",
        "resolved_horizon": "1W",
        "horizons": ["10min", "1h", "1D", "1W"],
        "point_in_time_input_only": True,
        "future_label_used": False,
        "horizon_distributions": {
            "1W": {
                "expected_return": 0.035,
                "uncertainty_spread": 0.04,
                "upside_probability": 0.72,
                "tail_loss_probability": 0.08,
            }
        },
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


class _FakeCursor:
    def __init__(self, *, fetchone_rows: list[dict[str, object]], fetchall_rows: list[dict[str, object]]) -> None:
        self._fetchone_rows = list(fetchone_rows)
        self._fetchall_rows = list(fetchall_rows)
        self.executed_sql: list[str] = []

    def execute(self, sql: str, params: object = None) -> None:
        del params
        self.executed_sql.append(sql)

    def fetchone(self) -> dict[str, object] | None:
        return self._fetchone_rows.pop(0) if self._fetchone_rows else None

    def fetchall(self) -> list[dict[str, object]]:
        return list(self._fetchall_rows)


if __name__ == "__main__":
    unittest.main()

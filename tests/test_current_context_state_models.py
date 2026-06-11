from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.model_01_background_context import generate_rows as generate_background_context
from models.model_01_background_context.evaluation import (
    assert_no_label_leakage as assert_no_m01_label_leakage,
    build_background_context_labels,
)
from models.model_02_target_state import generate_rows as generate_target_state
from models.model_02_target_state.evaluation import (
    assert_no_label_leakage as assert_no_m02_label_leakage,
    build_target_state_labels,
)
from models.model_03_event_state.contract import EVENT_IMPACT_CHANNELS as M03_EVENT_IMPACT_CHANNELS
from models.model_03_event_state import generate_rows as generate_event_state
from models.model_03_event_state.evaluation import (
    assert_no_label_leakage as assert_no_m03_label_leakage,
    build_event_state_labels,
)
from models.model_04_unified_decision import generate_rows as generate_unified_decision
from models.model_05_option_expression import generate_rows as generate_option_expression
from models.model_06_residual_event_governance import generate_rows as generate_residual_event_governance


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_CHAIN_FIELDS = {
    "alpha_confidence_vector",
    "dynamic_risk_policy_state",
    "position_projection_vector",
    "underlying_action_vector",
    "underlying_action_plan",
    "underlying_action_plan_ref",
    "event_context_vector",
    "event_context_vector_ref",
}


class BackgroundContextModelTests(unittest.TestCase):
    def test_generates_current_background_context_state(self) -> None:
        output = generate_background_context([_background_input()])[0]

        self.assertEqual(output["model_id"], "background_context_model")
        self.assertEqual(output["model_step"], "M01")
        self.assertIn("background_context_state_ref", output)
        self.assertIn("background_context_state", output)
        self.assertGreater(output["1_background_context_quality_score_1W"], 0.0)
        self.assertNotIn("target_candidate_id", output)
        assert_no_m01_label_leakage(output)

    def test_labels_are_offline_and_join_by_background_ref(self) -> None:
        output = generate_background_context([_background_input()])[0]
        labels = build_background_context_labels(
            [output],
            [
                {
                    "background_context_state_ref": output["background_context_state_ref"],
                    "future_market_volatility_1W": 0.20,
                    "background_context_realized_utility_1W": 0.11,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertAlmostEqual(labels[0]["background_context_realized_utility_1W"], 0.11)
        self.assertNotIn("future_market_volatility_1W", output)

    def test_script_fixture_and_review_defer_local_evidence(self) -> None:
        _assert_script_fixture_and_review(
            generate_script="scripts/models/model_01_background_context/generate_model_01_background_context.py",
            evaluate_script="scripts/models/model_01_background_context/evaluate_model_01_background_context.py",
            review_script="scripts/models/model_01_background_context/review_background_context_promotion.py",
            model_surface="model_01_background_context",
            expected_field="background_context_state",
        )

    def test_current_script_column_type_uses_model_01_prefix(self) -> None:
        script = _load_script("scripts/models/model_01_background_context/generate_model_01_background_context.py")

        self.assertEqual(script._column_type("1_market_risk_stress_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("background_context_state"), "JSONB")
        self.assertEqual(script._column_type("2_target_direction_score_1W"), "TEXT")


class TargetStateModelTests(unittest.TestCase):
    def test_generates_current_target_context_state_without_identity_leakage(self) -> None:
        background = generate_background_context([_background_input()])[0]
        output = generate_target_state([_target_input(background)])[0]

        self.assertEqual(output["model_id"], "target_state_model")
        self.assertEqual(output["model_step"], "M02")
        self.assertEqual(output["background_context_state_ref"], background["background_context_state_ref"])
        self.assertIn("target_context_state_ref", output)
        self.assertGreater(output["2_target_direction_score_1W"], 0.0)
        self.assert_no_key(output["target_context_state"], "symbol")
        self.assert_no_key(output["target_context_state"], "company_name")
        assert_no_m02_label_leakage(output)

    def test_labels_are_offline_and_join_by_target_ref(self) -> None:
        background = generate_background_context([_background_input()])[0]
        output = generate_target_state([_target_input(background)])[0]
        labels = build_target_state_labels(
            [output],
            [
                {
                    "target_context_state_ref": output["target_context_state_ref"],
                    "future_target_return_1W": 0.04,
                    "target_state_realized_utility_1W": 0.13,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["target_candidate_id"], "anon_target_001")
        self.assertNotIn("future_target_return_1W", output)

    def test_script_fixture_and_review_defer_local_evidence(self) -> None:
        _assert_script_fixture_and_review(
            generate_script="scripts/models/model_02_target_state/generate_model_02_target_state.py",
            evaluate_script="scripts/models/model_02_target_state/evaluate_model_02_target_state.py",
            review_script="scripts/models/model_02_target_state/review_target_state_promotion.py",
            model_surface="model_02_target_state",
            expected_field="target_context_state",
        )

    def test_current_script_column_type_uses_model_02_prefix(self) -> None:
        script = _load_script("scripts/models/model_02_target_state/generate_model_02_target_state.py")

        self.assertEqual(script._column_type("2_target_direction_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("target_context_state"), "JSONB")
        self.assertEqual(script._column_type("3_event_path_risk_score_1W"), "TEXT")

    def assert_no_key(self, value: object, forbidden: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotEqual(str(key), forbidden)
                self.assert_no_key(nested, forbidden)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_key(nested, forbidden)


class EventStateModelTests(unittest.TestCase):
    def test_generates_current_event_state_vector_from_accepted_events(self) -> None:
        background = generate_background_context([_background_input()])[0]
        target = generate_target_state([_target_input(background)])[0]
        output = generate_event_state([_event_input(background, target)])[0]

        self.assertEqual(output["model_id"], "event_state_model")
        self.assertEqual(output["model_step"], "M03")
        self.assertEqual(output["background_context_state_ref"], background["background_context_state_ref"])
        self.assertEqual(output["target_context_state_ref"], target["target_context_state_ref"])
        self.assertIn("event_state_vector_ref", output)
        self.assertGreater(output["3_event_path_risk_score_1W"], 0.0)
        self.assertFalse(output["event_state_vector"]["event_parameter_mutation_allowed"])
        self.assertIn("impact_channel_scores", output["event_state_vector"])
        self.assertNotIn("standalone_event_alpha", output)
        assert_no_m03_label_leakage(output)

    def test_option_sensitive_event_attributes_are_runtime_state_channels(self) -> None:
        background = generate_background_context([_background_input()])[0]
        target = generate_target_state([_target_input(background)])[0]
        output = generate_event_state(
            [
                _event_input(
                    background,
                    target,
                    accepted_event_contracts=[
                        {
                            "event_id": "evt_triple_witching_fixture",
                            "canonical_event_id": "evt_triple_witching_fixture",
                            "event_family_key": "triple_witching_calendar",
                            "event_time": "2026-06-19T09:30:00-04:00",
                            "available_time": "2026-06-19T09:30:00-04:00",
                            "event_intensity_score": 0.70,
                            "direction_bias_score": 0.0,
                            "target_relevance_score": 0.80,
                            "impact_channels": {
                                "underlying_price": 0.20,
                                "option_price": 0.85,
                                "volatility_surface": 0.90,
                                "option_liquidity_spread": 0.75,
                                "expiry_gamma_flow": 0.95,
                            },
                        }
                    ],
                )
            ]
        )[0]

        self.assertEqual(tuple(output["event_state_vector"]["impact_channel_scores"]["1D"]), M03_EVENT_IMPACT_CHANNELS)
        self.assertGreater(output["3_event_option_price_impact_score_1D"], output["3_event_underlying_price_impact_score_1D"])
        self.assertAlmostEqual(output["3_event_expiry_gamma_flow_impact_score_1D"], 0.95)

    def test_no_events_remain_neutral(self) -> None:
        background = generate_background_context([_background_input()])[0]
        target = generate_target_state([_target_input(background)])[0]
        output = generate_event_state([_event_input(background, target, accepted_event_contracts=[])])[0]

        self.assertEqual(output["3_event_path_risk_score_1W"], 0.0)
        self.assertEqual(output["3_event_option_price_impact_score_1W"], 0.0)
        self.assertEqual(output["event_state_vector"]["accepted_event_count"], 0)

    def test_labels_are_offline_and_join_by_event_ref(self) -> None:
        background = generate_background_context([_background_input()])[0]
        target = generate_target_state([_target_input(background)])[0]
        output = generate_event_state([_event_input(background, target)])[0]
        labels = build_event_state_labels(
            [output],
            [
                {
                    "event_state_vector_ref": output["event_state_vector_ref"],
                    "realized_event_response_1W": -0.02,
                    "event_state_realized_utility_1W": 0.04,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["target_candidate_id"], "anon_target_001")
        self.assertNotIn("realized_event_response_1W", output)

    def test_script_fixture_and_review_defer_local_evidence(self) -> None:
        _assert_script_fixture_and_review(
            generate_script="scripts/models/model_03_event_state/generate_model_03_event_state.py",
            evaluate_script="scripts/models/model_03_event_state/evaluate_model_03_event_state.py",
            review_script="scripts/models/model_03_event_state/review_event_state_promotion.py",
            model_surface="model_03_event_state",
            expected_field="event_state_vector",
        )

    def test_current_script_column_type_uses_model_03_prefix(self) -> None:
        script = _load_script("scripts/models/model_03_event_state/generate_model_03_event_state.py")

        self.assertEqual(script._column_type("3_event_path_risk_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("event_state_vector"), "JSONB")
        self.assertEqual(script._column_type("4_after_cost_edge_score_1W"), "TEXT")


class CurrentSixModelChainTests(unittest.TestCase):
    def test_current_m01_to_m06_chain_passes_refs_between_contracts(self) -> None:
        background = generate_background_context([_background_input()])[0]
        target = generate_target_state([_target_input(background)])[0]
        event = generate_event_state([_event_input(background, target)])[0]
        decision = generate_unified_decision([_decision_input(background, target, event)])[0]
        option = generate_option_expression([_option_input(background, event, decision)])[0]
        residual = generate_residual_event_governance([_residual_input(target, decision, option)])[0]

        self.assertEqual(decision["background_context_state_ref"], background["background_context_state_ref"])
        self.assertEqual(decision["target_context_state_ref"], target["target_context_state_ref"])
        self.assertEqual(decision["event_state_vector_ref"], event["event_state_vector_ref"])
        self.assertEqual(option["unified_decision_vector_ref"], decision["unified_decision_vector_ref"])
        self.assertEqual(residual["unified_decision_vector_ref"], decision["unified_decision_vector_ref"])
        self.assertEqual(residual["option_expression_plan_ref"], option["option_expression_plan_ref"])
        for row in (background, target, event, decision, option, residual):
            self.assert_no_retired_chain_fields(row)
        self.assertIn("background_context_state", background)
        self.assertIn("target_context_state", target)
        self.assertIn("event_state_vector", event)
        self.assertIn("unified_decision_vector", decision)
        self.assertIn("option_expression_plan", option)
        self.assertIn("event_risk_intervention", residual)

    def assert_no_retired_chain_fields(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key), RETIRED_CHAIN_FIELDS)
                self.assert_no_retired_chain_fields(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_retired_chain_fields(nested)


def _assert_script_fixture_and_review(*, generate_script: str, evaluate_script: str, review_script: str, model_surface: str, expected_field: str) -> None:
    for script in (generate_script, evaluate_script, review_script):
        help_result = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert help_result.returncode == 0, help_result.stderr
        assert "usage:" in help_result.stdout

    generate_result = subprocess.run(
        [sys.executable, generate_script],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert generate_result.returncode == 0, generate_result.stderr
    rows = json.loads(generate_result.stdout)
    assert len(rows) == 1
    assert expected_field in rows[0]

    with tempfile.TemporaryDirectory() as tmp:
        summary_path = Path(tmp) / "summary.json"
        review_path = Path(tmp) / "review.json"
        eval_result = subprocess.run(
            [sys.executable, evaluate_script, "--output-json", str(summary_path)],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert eval_result.returncode == 0, eval_result.stderr
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["summary"]["model_surface"] == model_surface
        assert summary["summary"]["promotion_gate_state"] == "deferred"

        review_result = subprocess.run(
            [sys.executable, review_script, "--evaluation-summary-json", str(summary_path), "--output-json", str(review_path)],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert review_result.returncode == 0, review_result.stderr
        review = json.loads(review_path.read_text(encoding="utf-8"))
        assert review["decision_status"] == "deferred"
        assert review["activation_allowed"] is False


def _background_input(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "market_return_10min": 0.01,
        "market_return_1h": 0.02,
        "market_return_1D": 0.03,
        "market_return_1W": 0.04,
        "market_trend_quality_score": 0.78,
        "market_volatility_pressure_score": 0.22,
        "market_liquidity_support_score": 0.86,
        "sector_relative_direction_score": 0.34,
        "sector_breadth_score": 0.72,
        "sector_dispersion_score": 0.18,
        "data_quality_score": 0.92,
        "coverage_score": 0.88,
    }
    row.update(overrides)
    return row


def _target_input(background: dict[str, object], **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": background["available_time"],
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "symbol": "AAPL",
        "background_context_state_ref": background["background_context_state_ref"],
        "background_context_state": background["background_context_state"]["score_payload"],  # type: ignore[index]
        "anonymous_target_feature_vector": {
            "target_return_1W": 0.62,
            "target_return_1D": 0.45,
            "target_trend_quality_score": 0.78,
            "target_volatility_pressure_score": 0.20,
            "target_transition_risk_score": 0.16,
            "target_liquidity_tradability_score": 0.88,
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
        },
    }
    row.update(overrides)
    return row


def _event_input(background: dict[str, object], target: dict[str, object], **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": target["available_time"],
        "tradeable_time": target["tradeable_time"],
        "target_candidate_id": target["target_candidate_id"],
        "background_context_state_ref": background["background_context_state_ref"],
        "target_context_state_ref": target["target_context_state_ref"],
        "target_context_state": target["target_context_state"]["score_payload"],  # type: ignore[index]
        "accepted_event_contracts": [
            {
                "event_id": "evt_fixture_canonical",
                "canonical_event_id": "evt_fixture_canonical",
                "event_time": "2026-05-07T10:10:00-04:00",
                "available_time": "2026-05-07T10:12:00-04:00",
                "event_category_type": "sec_filing",
                "event_intensity_score": 0.45,
                "direction_bias_score": -0.25,
                "target_relevance_score": 0.80,
                "uncertainty_score": 0.35,
                "path_risk_score": 0.28,
            }
        ],
    }
    row.update(overrides)
    return row


def _decision_input(background: dict[str, object], target: dict[str, object], event: dict[str, object]) -> dict[str, object]:
    return {
        "available_time": event["available_time"],
        "tradeable_time": event["tradeable_time"],
        "target_candidate_id": target["target_candidate_id"],
        "background_context_state_ref": background["background_context_state_ref"],
        "target_context_state_ref": target["target_context_state_ref"],
        "event_state_vector_ref": event["event_state_vector_ref"],
        "background_context_state": background["background_context_state"]["score_payload"],  # type: ignore[index]
        "target_context_state": target["target_context_state"]["score_payload"],  # type: ignore[index]
        "event_state_vector": event["event_state_vector"]["score_payload"],  # type: ignore[index]
        "quality_calibration_state": {"data_quality_score": 0.90, "walk_forward_reliability_score": 0.82, "out_of_distribution_score": 0.08},
        "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.85, "correlation_concentration_score": 0.20},
        "account_capacity_state": {"cash_capacity_score": 0.78, "drawdown_pressure_score": 0.12},
        "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
        "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
        "cost_friction_state": {"spread_cost_estimate": 0.001, "slippage_cost_estimate": 0.001, "fee_cost_estimate": 0.0005, "turnover_cost_estimate": 0.001},
        "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
        "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50_000_000, "liquidity_score": 0.95},
        "underlying_borrow_state": {"short_borrow_status": "available"},
        "risk_budget_state": {"risk_budget_available_score": 0.95},
        "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
    }


def _option_input(background: dict[str, object], event: dict[str, object], decision: dict[str, object]) -> dict[str, object]:
    return {
        "available_time": decision["available_time"],
        "tradeable_time": decision["tradeable_time"],
        "target_candidate_id": decision["target_candidate_id"],
        "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
        "option_chain_snapshot_ref": "chain_snapshot_fixture",
        "option_quote_available_time": "2026-05-07T10:30:05-04:00",
        "underlying_quote_snapshot_ref": "underlying_quote_fixture",
        "underlying_reference_price": 100.25,
        "direct_underlying_intent": decision["direct_underlying_intent"],
        "background_context_state": background["background_context_state"]["score_payload"],  # type: ignore[index]
        "event_state_vector": event["event_state_vector"]["score_payload"],  # type: ignore[index]
        "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
        "option_contract_candidates": [
            {
                "contract_ref": "AAPL_CALL_GOOD",
                "quote_snapshot_ref": "qs_call_good",
                "quote_available_time": "2026-05-07T10:30:05-04:00",
                "quote_age_seconds": 12,
                "strike": 102,
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
                "volume": 1200,
                "open_interest": 6500,
                "contract_multiplier": 100,
            }
        ],
    }


def _residual_input(target: dict[str, object], decision: dict[str, object], option: dict[str, object]) -> dict[str, object]:
    return {
        "available_time": decision["available_time"],
        "tradeable_time": decision["tradeable_time"],
        "target_candidate_id": decision["target_candidate_id"],
        "symbol_for_join_only": "AAPL",
        "sector_type": "technology",
        "target_context_state_ref": target["target_context_state_ref"],
        "unified_decision_vector_ref": decision["unified_decision_vector_ref"],
        "option_expression_plan_ref": option["option_expression_plan_ref"],
        "target_context_state": target["target_context_state"]["score_payload"],  # type: ignore[index]
        "direct_underlying_intent": decision["direct_underlying_intent"],
        "option_expression_plan": option["option_expression_plan"],
        "event_observations": [
            {
                "event_id": "evt_fixture_canonical",
                "canonical_event_id": "evt_fixture_canonical",
                "dedup_status": "new_information",
                "source_priority": 1,
                "event_time": "2026-05-07T10:10:00-04:00",
                "available_time": "2026-05-07T10:12:00-04:00",
                "event_category_type": "sec_filing",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "sector_type": "technology",
                "event_intensity_score": 0.9,
                "direction_bias_score": -0.7,
                "target_relevance_score": 1.0,
                "scope_confidence_score": 0.9,
            }
        ],
    }


def _load_script(path: str):
    script = REPO_ROOT / path
    spec = importlib.util.spec_from_file_location(script.stem, script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from models.model_07_underlying_action import generate_rows
from models.model_07_underlying_action.evaluation import build_plan_quality_labels


FORBIDDEN_TERMS = {
    "order_type",
    "route",
    "time_in_force",
    "send_order",
    "replace_order",
    "cancel_order",
    "broker_order_id",
    "option_symbol",
    "option_right",
    "strike",
    "dte",
    "delta",
    "theta",
    "vega",
    "specific_contract_ref",
    "final_action",
}


class UnderlyingActionModelTests(unittest.TestCase):
    def test_increase_long_uses_pending_adjusted_effective_exposure(self) -> None:
        row = _base_row(
            current_underlying_position_state={"current_underlying_exposure_score": 0.10},
            pending_underlying_order_state={"pending_underlying_exposure_score": 0.10, "pending_fill_probability_estimate": 0.50},
            position_projection_vector={
                "6_dominant_projection_horizon": "390min",
                "6_target_exposure_score_390min": 0.40,
                "6_projection_confidence_score_390min": 0.92,
                "6_risk_budget_fit_score_390min": 0.95,
                "6_cost_to_adjust_position_score_390min": 0.10,
                "6_position_state_stability_score_390min": 0.90,
            },
        )

        output = generate_rows([row])[0]
        plan = output["underlying_action_plan"]
        exposure = plan["exposure_plan"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "increase_long")
        self.assertAlmostEqual(exposure["effective_current_underlying_exposure_score"], 0.15)
        self.assertAlmostEqual(exposure["underlying_exposure_gap_score"], 0.25)
        self.assertGreater(exposure["planned_incremental_exposure_score"], 0.0)
        self.assertEqual(plan["handoff_to_layer_8"]["underlying_path_direction"], "bullish")
        self.assert_no_forbidden_terms(output)

    def test_pending_exposure_prevents_duplicate_underlying_plan(self) -> None:
        row = _base_row(
            current_underlying_position_state={"current_underlying_exposure_score": 0.10},
            pending_underlying_order_state={"pending_underlying_exposure_score": 0.30, "pending_fill_probability_estimate": 1.0},
            position_projection_vector={
                "6_dominant_projection_horizon": "390min",
                "6_target_exposure_score_390min": 0.40,
                "6_projection_confidence_score_390min": 0.95,
                "6_risk_budget_fit_score_390min": 0.95,
                "6_cost_to_adjust_position_score_390min": 0.05,
                "6_position_state_stability_score_390min": 0.95,
            },
        )

        output = generate_rows([row])[0]
        plan = output["underlying_action_plan"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "maintain")
        self.assertAlmostEqual(plan["exposure_plan"]["effective_current_underlying_exposure_score"], 0.40)
        self.assertAlmostEqual(plan["exposure_plan"]["planned_incremental_exposure_score"], 0.0)
        self.assertIn("existing_state_remains_valid_or_adjustment_not_worth_cost", plan["reason_codes"])

    def test_no_trade_is_distinct_from_maintain_for_flat_small_gap(self) -> None:
        row = _base_row(
            current_underlying_position_state={"current_underlying_exposure_score": 0.0},
            position_projection_vector={"6_dominant_projection_horizon": "60min", "6_target_exposure_score_60min": 0.01},
        )

        output = generate_rows([row])[0]

        self.assertEqual(output["7_resolved_underlying_action_type"], "no_trade")
        self.assertIn("no_new_underlying_operation", output["underlying_action_plan"]["reason_codes"])
        self.assertEqual(output["underlying_action_plan"]["entry_plan"]["entry_style"], "no_entry")

    def test_bearish_flat_without_short_borrow_does_not_select_option_contract(self) -> None:
        row = _base_row(
            alpha_confidence_vector={
                "5_alpha_confidence_score_390min": 0.90,
                "5_expected_return_score_390min": -0.05,
                "5_path_quality_score_390min": 0.85,
                "5_reversal_risk_score_390min": 0.10,
                "5_drawdown_risk_score_390min": 0.20,
            },
            current_underlying_position_state={"current_underlying_exposure_score": 0.0},
            position_projection_vector={
                "6_dominant_projection_horizon": "390min",
                "6_target_exposure_score_390min": -0.40,
                "6_projection_confidence_score_390min": 0.92,
                "6_risk_budget_fit_score_390min": 0.95,
                "6_cost_to_adjust_position_score_390min": 0.05,
                "6_position_state_stability_score_390min": 0.90,
            },
            underlying_borrow_state={"short_borrow_status": "unavailable"},
        )

        output = generate_rows([row])[0]
        plan = output["underlying_action_plan"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "bearish_underlying_path_but_no_short_allowed")
        self.assertIn("direct_short_not_allowed", plan["reason_codes"])
        self.assert_no_forbidden_terms(output)

    def test_short_plan_uses_side_neutral_price_bounds(self) -> None:
        row = _base_row(
            alpha_confidence_vector={
                "5_alpha_confidence_score_390min": 0.90,
                "5_expected_return_score_390min": -0.06,
                "5_path_quality_score_390min": 0.85,
                "5_reversal_risk_score_390min": 0.10,
                "5_drawdown_risk_score_390min": 0.20,
            },
            position_projection_vector={
                "6_dominant_projection_horizon": "390min",
                "6_target_exposure_score_390min": -0.45,
                "6_projection_confidence_score_390min": 0.93,
                "6_risk_budget_fit_score_390min": 0.95,
                "6_cost_to_adjust_position_score_390min": 0.05,
                "6_position_state_stability_score_390min": 0.92,
            },
            underlying_borrow_state={"short_borrow_status": "available"},
        )

        output = generate_rows([row])[0]
        plan = output["underlying_action_plan"]
        entry = plan["entry_plan"]
        risk = plan["risk_plan"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "open_short")
        self.assertEqual(plan["price_path_expectation"]["underlying_path_direction"], "bearish")
        self.assertLess(entry["worst_acceptable_entry_price"], entry["reference_price"])
        self.assertGreater(risk["stop_loss_price"], entry["reference_price"])
        self.assertLess(risk["take_profit_price"], entry["reference_price"])

    def test_opposite_long_to_short_closes_and_reassesses_instead_of_reversing(self) -> None:
        row = _base_row(
            current_underlying_position_state={"current_underlying_exposure_score": 0.30},
            position_projection_vector={
                "6_dominant_projection_horizon": "390min",
                "6_target_exposure_score_390min": -0.25,
                "6_projection_confidence_score_390min": 0.95,
                "6_risk_budget_fit_score_390min": 0.95,
                "6_cost_to_adjust_position_score_390min": 0.05,
                "6_position_state_stability_score_390min": 0.90,
            },
            underlying_borrow_state={"short_borrow_status": "available"},
        )

        output = generate_rows([row])[0]
        reasons = output["underlying_action_plan"]["reason_codes"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "close_long")
        self.assertIn("opposite_exposure_detected", reasons)
        self.assertIn("close_then_reassess_candidate", reasons)

    def test_hard_gate_blocks_new_exposure(self) -> None:
        row = _base_row(underlying_quote_state={"reference_price": 100.0, "bid_price": 99.9, "ask_price": 100.1, "halt_status": "halted"})

        output = generate_rows([row])[0]
        plan = output["underlying_action_plan"]

        self.assertEqual(output["7_resolved_underlying_action_type"], "no_trade")
        self.assertEqual(output["7_underlying_trade_eligibility_score_390min"], 0.0)
        self.assertIn("halt_status_not_active", plan["reason_codes"])

    def test_plan_quality_labels_are_offline_and_join_by_plan_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_plan_quality_labels(
            [output],
            [
                {
                    "underlying_action_plan_ref": output["underlying_action_plan_ref"],
                    "entry_price_hit": True,
                    "target_hit_time": "2026-05-07T11:00:00-04:00",
                    "stop_hit_time": "2026-05-07T12:00:00-04:00",
                    "realized_underlying_return": 0.04,
                    "slippage_pct": 0.001,
                    "spread_cost_pct": 0.001,
                    "realized_max_favorable_excursion": 0.05,
                    "realized_max_adverse_excursion": -0.01,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0]["planned_entry_fill_probability_label"])
        self.assertTrue(labels[0]["target_price_hit_before_stop_label"])
        self.assertAlmostEqual(labels[0]["spread_adjusted_return"], 0.038)
        self.assertAlmostEqual(labels[0]["reward_risk_realized_ratio"], 5.0)

    def assert_no_forbidden_terms(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key).lower(), FORBIDDEN_TERMS)
                self.assert_no_forbidden_terms(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_forbidden_terms(nested)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "alpha_confidence_vector_ref": "acv_fixture",
        "position_projection_vector_ref": "ppv_fixture",
        "alpha_confidence_vector": {
            "5_alpha_confidence_score_390min": 0.90,
            "5_expected_return_score_390min": 0.05,
            "5_path_quality_score_390min": 0.85,
            "5_reversal_risk_score_390min": 0.10,
            "5_drawdown_risk_score_390min": 0.20,
        },
        "position_projection_vector": {
            "6_dominant_projection_horizon": "390min",
            "6_target_exposure_score_390min": 0.40,
            "6_projection_confidence_score_390min": 0.92,
            "6_risk_budget_fit_score_390min": 0.95,
            "6_cost_to_adjust_position_score_390min": 0.08,
            "6_position_state_stability_score_390min": 0.90,
        },
        "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
        "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
        "underlying_quote_state": {"reference_price": 100.0, "bid_price": 99.95, "ask_price": 100.05, "halt_status": "active"},
        "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50_000_000, "liquidity_score": 0.95},
        "underlying_borrow_state": {"short_borrow_status": "unavailable"},
        "risk_budget_state": {"risk_budget_fit_score": 0.95},
        "policy_gate_state": {},
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()

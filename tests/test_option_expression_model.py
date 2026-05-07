from __future__ import annotations

import unittest

from models.model_08_option_expression import generate_rows
from models.model_08_option_expression.evaluation import assert_no_label_leakage, build_option_expression_labels


FORBIDDEN_TERMS = {
    "order_type",
    "route",
    "routing_destination",
    "time_in_force",
    "send_order",
    "replace_order",
    "cancel_order",
    "broker_order_id",
    "broker_account_id",
    "execution_instruction",
    "order_instruction",
    "final_action",
    "final_order_quantity",
    "order_quantity",
}


class OptionExpressionModelTests(unittest.TestCase):
    def test_bullish_underlying_thesis_selects_long_call_contract(self) -> None:
        output = generate_rows([_base_row()])[0]
        plan = output["option_expression_plan"]

        self.assertEqual(output["8_resolved_expression_type"], "long_call")
        self.assertEqual(output["8_resolved_option_right"], "call")
        self.assertEqual(output["8_resolved_selected_contract_ref"], "AAPL_CALL_GOOD")
        self.assertGreater(output["8_option_expression_confidence_score_390min"], 0.0)
        self.assertGreater(output["8_option_contract_fit_score_390min"], 0.0)
        self.assertEqual(plan["selected_contract"]["contract_ref"], "AAPL_CALL_GOOD")
        self.assertIn("preferred_dte_range", plan["contract_constraints"])
        self.assertEqual(plan["contract_constraints"]["allow_0dte"], False)
        self.assertIn("point_in_time_contract_candidate_selected", plan["reason_codes"])
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_bearish_no_direct_short_can_select_long_put(self) -> None:
        row = _base_row(
            underlying_action_plan={
                "planned_underlying_action_type": "bearish_underlying_path_but_no_short_allowed",
                "action_side": "bearish_no_direct_short",
                "dominant_horizon": "390min",
                "handoff_to_layer_8": {
                    **_handoff(),
                    "underlying_path_direction": "bearish",
                    "expected_favorable_move_pct": 0.045,
                    "expected_adverse_move_pct": -0.018,
                },
            }
        )
        output = generate_rows([row])[0]

        self.assertEqual(output["8_resolved_expression_type"], "long_put")
        self.assertEqual(output["8_resolved_option_right"], "put")
        self.assertEqual(output["8_resolved_selected_contract_ref"], "AAPL_PUT_GOOD")
        self.assertLess(output["8_option_expression_direction_score_390min"], 0.0)
        self.assert_no_forbidden_terms(output)

    def test_policy_block_outputs_no_option_expression(self) -> None:
        output = generate_rows([_base_row(option_expression_policy={"allow_option_expression": "false"})])[0]

        self.assertEqual(output["8_resolved_expression_type"], "no_option_expression")
        self.assertIsNone(output["8_resolved_selected_contract_ref"])
        self.assertEqual(output["8_option_expression_eligibility_score_390min"], 0.0)
        self.assertIn("option_expression_policy_blocked", output["option_expression_plan"]["reason_codes"])

    def test_maintain_and_pending_option_exposure_do_not_create_overlay(self) -> None:
        maintain_output = generate_rows([_base_row(underlying_action_plan={"planned_underlying_action_type": "maintain", "action_side": "long", "dominant_horizon": "390min", "handoff_to_layer_8": _handoff()})])[0]
        pending_output = generate_rows([_base_row(pending_option_premium_exposure=250.0, pending_option_fill_probability_estimate=0.75)])[0]

        self.assertEqual(maintain_output["8_resolved_expression_type"], "no_option_expression")
        self.assertIn("underlying_action_maintain", maintain_output["8_resolved_no_option_reason_codes"])
        self.assertEqual(pending_output["8_resolved_expression_type"], "no_option_expression")
        self.assertIn("pending_option_exposure_detected", pending_output["8_resolved_no_option_reason_codes"])

    def test_labels_are_offline_and_join_by_plan_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_option_expression_labels(
            [output],
            [
                {
                    "option_expression_plan_ref": output["option_expression_plan_ref"],
                    "realized_option_return_390min": 0.42,
                    "target_premium_hit_before_stop_label_390min": True,
                    "selected_contract_regret_vs_best_candidate_390min": 0.03,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0]["target_premium_hit_before_stop_label_390min"])
        self.assertNotIn("realized_option_return_390min", output)

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
        "underlying_action_plan_ref": "uap_fixture",
        "underlying_action_plan": {
            "planned_underlying_action_type": "increase_long",
            "action_side": "long",
            "dominant_horizon": "390min",
            "handoff_to_layer_8": _handoff(),
        },
        "market_context_state": {"1_market_risk_stress_score": 0.20, "1_market_liquidity_support_score": 0.85},
        "event_context_vector": {"4_event_gap_risk_score_390min": 0.20, "4_event_uncertainty_score_390min": 0.15},
        "option_expression_policy": {"max_option_spread_pct": 0.18, "iv_rank_ceiling": 0.75},
        "option_contract_candidates": [
            {
                "contract_ref": "AAPL_CALL_GOOD",
                "quote_snapshot_ref": "qs_call_good",
                "quote_age_seconds": 12,
                "strike": 102,
                "contract_multiplier": 100,
                "right": "call",
                "expiration": "2026-05-15",
                "dte": 8,
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
            },
            {
                "contract_ref": "AAPL_CALL_WIDE",
                "right": "call",
                "expiration": "2026-05-15",
                "dte": 8,
                "delta": 0.48,
                "theta": -0.07,
                "vega": 0.11,
                "iv_rank": 0.40,
                "bid": 1.00,
                "ask": 1.60,
                "volume": 20,
                "open_interest": 80,
            },
            {
                "contract_ref": "AAPL_PUT_GOOD",
                "quote_snapshot_ref": "qs_put_good",
                "quote_age_seconds": 15,
                "strike": 98,
                "contract_multiplier": 100,
                "right": "put",
                "expiration": "2026-05-15",
                "dte": 8,
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


def _handoff() -> dict[str, object]:
    return {
        "underlying_path_direction": "bullish",
        "expected_entry_price": 100.0,
        "expected_target_price": 105.0,
        "target_price_low": 103.0,
        "target_price_high": 106.0,
        "stop_loss_price": 98.0,
        "thesis_invalidation_price": 97.5,
        "expected_holding_time_minutes": 390,
        "path_quality_score": 0.82,
        "reversal_risk_score": 0.18,
        "drawdown_risk_score": 0.22,
        "expected_favorable_move_pct": 0.05,
        "expected_adverse_move_pct": -0.02,
        "entry_price_assumption": "limit_or_pullback",
        "underlying_action_confidence_score": 0.78,
    }


if __name__ == "__main__":
    unittest.main()

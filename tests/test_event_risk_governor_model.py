from __future__ import annotations

import unittest

from models.model_10_event_risk_governor import generate_rows
from models.model_10_event_risk_governor.evaluation import assert_no_label_leakage, build_event_risk_governor_labels
from models.model_10_event_risk_governor.generator import _validate_no_forbidden_output


FORBIDDEN_TERMS = {
    "buy",
    "sell",
    "hold",
    "alpha_confidence",
    "target_exposure",
    "position_size",
    "option_contract",
    "option_symbol",
    "strike",
    "dte",
    "delta",
    "order_instruction",
    "order_type",
    "broker_order_id",
    "final_action",
    "future_return",
    "realized_pnl",
}


class EventRiskGovernorTests(unittest.TestCase):
    def test_filters_by_available_time_and_scores_scope_without_actions(self) -> None:
        output = generate_rows([_base_row()])[0]
        vector = output["event_context_vector"]
        diagnostics = output["event_risk_governor_diagnostics"]

        self.assertEqual(diagnostics["visible_event_count"], 2)
        self.assertEqual(diagnostics["canonical_event_count"], 1)
        self.assertGreater(vector["10_event_presence_score_1D"], 0.0)
        self.assertLess(vector["10_event_direction_bias_score_1D"], 0.0)
        self.assertLess(vector["10_event_symbol_impact_score_1D"], 0.0)
        self.assertGreater(abs(vector["10_event_symbol_impact_score_1D"]), abs(vector["10_event_market_impact_score_1D"]))
        self.assertEqual(
            diagnostics["dominant_impact_scope_by_horizon"]["10_event_dominant_impact_scope_1D"],
            "symbol",
        )
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_no_event_defaults_are_neutral_not_null(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[])
        output = generate_rows([row])[0]
        vector = output["event_context_vector"]

        self.assertEqual(vector["10_event_presence_score_1W"], 0.0)
        self.assertEqual(vector["10_event_direction_bias_score_1W"], 0.0)
        self.assertEqual(vector["10_event_market_impact_score_1W"], 0.0)
        self.assertGreater(vector["10_event_context_quality_score_1W"], 0.0)

    def test_crypto_context_uses_direct_underlying_without_option_requirement(self) -> None:
        output = generate_rows([
            _base_row(
                asset_class="crypto",
                underlying_action_plan_ref="uap_btc_fixture",
                underlying_action_vector_ref="uav_btc_fixture",
            )
        ])[0]

        self.assertEqual(output["asset_expression_route"], "direct_underlying_only")
        self.assertEqual(output["base_underlying_action_plan_ref"], "uap_btc_fixture")
        self.assertNotIn("base_trading_guidance_record_ref", output)
        self.assertNotIn("option_expression_plan_ref", output)
        self.assertFalse(output["event_risk_governor_diagnostics"]["underlying_thesis_context"]["option_expression_required_for_governor"])
        self.assertFalse(output["event_risk_governor_diagnostics"]["underlying_thesis_context"]["layer_8_trading_guidance_required_for_governor"])
        self.assert_no_forbidden_terms(output)

    def test_price_action_event_maps_to_microstructure_reversal_risk(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[
            {
                "event_id": "evt_false_breakout",
                "canonical_event_id": "evt_false_breakout",
                "dedup_status": "canonical",
                "event_time": "2026-05-07T10:25:00-04:00",
                "available_time": "2026-05-07T10:26:00-04:00",
                "event_category_type": "price_action",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "event_intensity_score": 0.8,
                "direction_bias_score": -0.6,
                "target_relevance_score": 1.0,
            }
        ])

        output = generate_rows([row])[0]
        vector = output["event_context_vector"]
        encoded = output["event_risk_governor_diagnostics"]["encoded_events"][0]

        self.assertEqual(encoded["event_native_scope_type"], "price_action")
        self.assertLess(vector["10_event_microstructure_impact_score_1h"], 0.0)
        self.assertGreater(vector["10_event_reversal_risk_score_1h"], 0.0)
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_earnings_shell_outputs_underlying_and_option_impact_surfaces(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[
            {
                "event_id": "evt_earnings_shell",
                "canonical_event_id": "evt_earnings_shell",
                "dedup_status": "canonical",
                "event_time": "2026-05-07T16:05:00-04:00",
                "available_time": "2026-05-07T10:20:00-04:00",
                "event_category_type": "earnings_guidance",
                "event_lifecycle_state": "pre_event_window",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "event_intensity_score": 0.7,
                "target_relevance_score": 1.0,
            }
        ])

        output = generate_rows([row])[0]
        vector = output["event_context_vector"]
        encoded = output["event_risk_governor_diagnostics"]["encoded_events"][0]

        self.assertIn("10_event_underlying_impact_score_1D", vector)
        self.assertIn("10_event_option_impact_score_1D", vector)
        self.assertGreater(vector["10_event_underlying_impact_score_1D"], 0.0)
        self.assertGreater(vector["10_event_option_impact_score_1D"], 0.0)
        self.assertIn("iv_expansion", encoded["option_impact_mechanisms"])
        self.assertIn("iv_crush_risk", encoded["option_impact_mechanisms"])
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_negative_macro_impact_preserves_unsigned_risk_magnitude(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[
            {
                "event_id": "evt_macro_shock",
                "canonical_event_id": "evt_macro_shock",
                "dedup_status": "canonical",
                "event_time": "2026-05-07T10:20:00-04:00",
                "available_time": "2026-05-07T10:21:00-04:00",
                "event_category_type": "macro_release",
                "scope_type": "macro",
                "event_intensity_score": 0.8,
                "direction_bias_score": -0.7,
                "target_relevance_score": 0.8,
            }
        ])

        output = generate_rows([row])[0]
        vector = output["event_context_vector"]

        self.assertLess(vector["10_event_market_impact_score_1D"], 0.0)
        self.assertGreater(vector["10_event_scope_escalation_risk_score_1D"], 0.0)
        self.assertGreater(vector["10_event_contagion_risk_score_1D"], 0.0)

    def test_direction_neutral_macro_event_preserves_scope_impact_and_risk(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[
            {
                "event_id": "evt_macro_uncertainty",
                "canonical_event_id": "evt_macro_uncertainty",
                "dedup_status": "canonical",
                "event_time": "2026-05-07T10:20:00-04:00",
                "available_time": "2026-05-07T10:21:00-04:00",
                "event_category_type": "macro_release",
                "scope_type": "macro",
                "event_intensity_score": 0.8,
                "target_relevance_score": 0.8,
            }
        ])

        output = generate_rows([row])[0]
        vector = output["event_context_vector"]
        diagnostics = output["event_risk_governor_diagnostics"]

        self.assertEqual(vector["10_event_direction_bias_score_1D"], 0.0)
        self.assertGreater(vector["10_event_market_impact_score_1D"], 0.0)
        self.assertGreater(vector["10_event_scope_escalation_risk_score_1D"], 0.0)
        self.assertGreater(vector["10_event_contagion_risk_score_1D"], 0.0)
        self.assertEqual(
            diagnostics["dominant_impact_scope_by_horizon"]["10_event_dominant_impact_scope_1D"],
            "market",
        )

    def test_weak_direction_bias_preserves_scope_impact_and_risk_magnitude(self) -> None:
        row = _base_row(m10_event_risk_governor_data_acquisition=[
            {
                "event_id": "evt_macro_weak_bias",
                "canonical_event_id": "evt_macro_weak_bias",
                "dedup_status": "canonical",
                "event_time": "2026-05-07T10:20:00-04:00",
                "available_time": "2026-05-07T10:21:00-04:00",
                "event_category_type": "macro_release",
                "scope_type": "macro",
                "event_intensity_score": 0.8,
                "direction_bias_score": 0.05,
                "target_relevance_score": 0.8,
            }
        ])

        output = generate_rows([row])[0]
        vector = output["event_context_vector"]

        self.assertAlmostEqual(vector["10_event_direction_bias_score_1D"], 0.05)
        self.assertGreater(vector["10_event_market_impact_score_1D"], 0.5)
        self.assertGreater(vector["10_event_scope_escalation_risk_score_1D"], 0.25)
        self.assertGreater(vector["10_event_contagion_risk_score_1D"], 0.3)

    def test_forbidden_output_diagnostic_names_layer_ten(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden Layer 10 output field"):
            _validate_no_forbidden_output({"buy": True})

    def test_labels_are_offline_and_join_by_vector_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_event_risk_governor_labels(
            [output],
            [
                {
                    "event_context_vector_ref": output["event_context_vector_ref"],
                    "realized_symbol_move_after_event_1W": -0.04,
                    "post_event_gap_realization_1W": 0.02,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["event_context_vector_ref"], output["event_context_vector_ref"])
        self.assertAlmostEqual(labels[0]["realized_symbol_move_after_event_1W"], -0.04)
        self.assertNotIn("realized_symbol_move_after_event_1W", output)

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
        "symbol_for_join_only": "AAPL",
        "sector_type": "technology",
        "market_context_state_ref": "mcs_fixture",
        "sector_context_state_ref": "scs_fixture",
        "target_context_state_ref": "tcs_fixture",
        "target_context_state": {"3_target_direction_score_1W": 0.5, "3_target_direction_score_1D": 0.4},
        "m10_event_risk_governor_data_acquisition": [
            {
                "event_id": "evt_canonical",
                "canonical_event_id": "evt_canonical",
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
            },
            {
                "event_id": "evt_duplicate_news",
                "canonical_event_id": "evt_canonical",
                "dedup_status": "covered_by_canonical_event",
                "source_priority": 4,
                "event_time": "2026-05-07T10:15:00-04:00",
                "available_time": "2026-05-07T10:18:00-04:00",
                "event_category_type": "news",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "direction_bias_score": -0.5,
            },
            {
                "event_id": "evt_future_revision",
                "dedup_status": "new_information",
                "event_time": "2026-05-07T10:35:00-04:00",
                "available_time": "2026-05-07T10:40:00-04:00",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "direction_bias_score": 0.9,
            },
        ],
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()

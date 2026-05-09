from __future__ import annotations

import unittest

from models.model_04_event_overlay import generate_rows
from models.model_04_event_overlay.evaluation import assert_no_label_leakage, build_event_overlay_labels


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


class EventOverlayModelTests(unittest.TestCase):
    def test_filters_by_available_time_and_scores_scope_without_actions(self) -> None:
        output = generate_rows([_base_row()])[0]
        vector = output["event_context_vector"]
        diagnostics = output["event_overlay_diagnostics"]

        self.assertEqual(diagnostics["visible_event_count"], 2)
        self.assertEqual(diagnostics["canonical_event_count"], 1)
        self.assertGreater(vector["4_event_presence_score_60min"], 0.0)
        self.assertLess(vector["4_event_direction_bias_score_60min"], 0.0)
        self.assertGreater(vector["4_event_symbol_impact_score_60min"], vector["4_event_market_impact_score_60min"])
        self.assertEqual(
            diagnostics["dominant_impact_scope_by_horizon"]["4_event_dominant_impact_scope_60min"],
            "symbol",
        )
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_no_event_defaults_are_neutral_not_null(self) -> None:
        row = _base_row(source_04_event_overlay=[])
        output = generate_rows([row])[0]
        vector = output["event_context_vector"]

        self.assertEqual(vector["4_event_presence_score_390min"], 0.0)
        self.assertEqual(vector["4_event_direction_bias_score_390min"], 0.0)
        self.assertEqual(vector["4_event_market_impact_score_390min"], 0.0)
        self.assertGreater(vector["4_event_context_quality_score_390min"], 0.0)

    def test_price_action_event_maps_to_microstructure_reversal_risk(self) -> None:
        row = _base_row(source_04_event_overlay=[
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
        encoded = output["event_overlay_diagnostics"]["encoded_events"][0]

        self.assertEqual(encoded["event_native_scope_type"], "price_action")
        self.assertGreater(vector["4_event_microstructure_impact_score_15min"], 0.0)
        self.assertGreater(vector["4_event_reversal_risk_score_15min"], 0.0)
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_labels_are_offline_and_join_by_vector_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_event_overlay_labels(
            [output],
            [
                {
                    "event_context_vector_ref": output["event_context_vector_ref"],
                    "realized_symbol_move_after_event_390min": -0.04,
                    "post_event_gap_realization_390min": 0.02,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["event_context_vector_ref"], output["event_context_vector_ref"])
        self.assertAlmostEqual(labels[0]["realized_symbol_move_after_event_390min"], -0.04)
        self.assertNotIn("realized_symbol_move_after_event_390min", output)

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
        "target_context_state": {"3_target_direction_score_390min": 0.5, "3_target_direction_score_60min": 0.4},
        "source_04_event_overlay": [
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

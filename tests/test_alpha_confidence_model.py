from __future__ import annotations

import unittest

from models.model_04_alpha_confidence import generate_rows
from models.model_04_alpha_confidence.evaluation import assert_no_label_leakage, build_alpha_confidence_labels


FORBIDDEN_TERMS = {
    "buy",
    "sell",
    "hold",
    "target_exposure",
    "position_size",
    "account_risk_allocation",
    "option_contract",
    "option_symbol",
    "strike",
    "dte",
    "delta",
    "order_type",
    "broker_order_id",
    "execution_result",
    "final_action",
    "future_fill",
    "realized_pnl",
}


class AlphaConfidenceModelTests(unittest.TestCase):
    def test_base_state_alpha_plus_event_adjustment_produces_final_vector(self) -> None:
        output = generate_rows([_base_row()])[0]
        vector = output["alpha_confidence_vector"]
        base = output["base_alpha_vector"]

        self.assertLess(vector["4_alpha_direction_score_390min"], 0.0)
        self.assertNotEqual(vector["4_alpha_strength_score_390min"], base["4_base_alpha_strength_score_390min"])
        self.assertGreater(vector["4_alpha_confidence_score_390min"], 0.0)
        self.assertIn("4_base_alpha_direction_score_390min", base)
        self.assertIn("high_quality_event_override", output["alpha_confidence_diagnostics"]["horizon_reason_codes"]["390min"])
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_no_edge_policy_keeps_direction_strength_and_tradability_low(self) -> None:
        output = generate_rows([_base_row(target_context_state={}, event_context_vector={})])[0]
        vector = output["alpha_confidence_vector"]

        self.assertEqual(vector["4_alpha_direction_score_390min"], 0.0)
        self.assertEqual(vector["4_alpha_strength_score_390min"], 0.0)
        self.assertLess(vector["4_alpha_tradability_score_390min"], 0.5)
        self.assertIn("no_material_alpha_edge", output["alpha_confidence_diagnostics"]["horizon_reason_codes"]["390min"])

    def test_labels_are_offline_and_join_by_vector_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_alpha_confidence_labels(
            [output],
            [
                {
                    "alpha_confidence_vector_ref": output["alpha_confidence_vector_ref"],
                    "forward_return_390min": -0.05,
                    "idiosyncratic_residual_return_390min": -0.04,
                    "alpha_tradable_label_390min": True,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0]["alpha_tradable_label_390min"])
        self.assertNotIn("forward_return_390min", output)

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
        "market_context_state_ref": "mcs_fixture",
        "sector_context_state_ref": "scs_fixture",
        "target_context_state_ref": "tcs_fixture",
        "event_context_vector_ref": "ecv_fixture",
        "market_context_state": {
            "1_market_risk_stress_score": 0.20,
            "1_market_liquidity_support_score": 0.85,
            "1_state_quality_score": 0.90,
        },
        "sector_context_state": {
            "2_sector_context_support_quality_score": 0.80,
            "2_state_quality_score": 0.88,
        },
        "target_context_state": {
            "3_target_direction_score_390min": 0.40,
            "3_target_trend_quality_score_390min": 0.75,
            "3_target_path_stability_score_390min": 0.80,
            "3_target_noise_score_390min": 0.20,
            "3_target_transition_risk_score_390min": 0.15,
            "3_context_direction_alignment_score_390min": 0.70,
            "3_context_support_quality_score_390min": 0.80,
            "3_tradability_score_390min": 0.85,
            "3_state_quality_score": 0.90,
            "3_beta_dependency_score_390min": 0.20,
        },
        "event_context_vector": {
            "8_event_presence_score_390min": 1.0,
            "8_event_intensity_score_390min": 0.95,
            "8_event_target_relevance_score_390min": 0.90,
            "8_event_context_quality_score_390min": 0.95,
            "8_event_direction_bias_score_390min": -0.85,
            "8_event_context_alignment_score_390min": -0.60,
            "8_event_uncertainty_score_390min": 0.20,
            "8_event_reversal_risk_score_390min": 0.30,
            "8_event_gap_risk_score_390min": 0.40,
            "8_event_liquidity_disruption_score_390min": 0.10,
        },
        "quality_calibration_state": {
            "sample_support_score": 0.85,
            "walk_forward_reliability_score": 0.80,
            "model_ensemble_agreement_score": 0.85,
            "model_disagreement_score": 0.10,
            "out_of_distribution_score": 0.10,
            "data_quality_score": 0.90,
        },
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()

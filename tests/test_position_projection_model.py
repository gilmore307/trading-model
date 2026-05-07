from __future__ import annotations

import unittest

from models.model_06_position_projection import generate_rows
from models.model_06_position_projection.evaluation import assert_no_label_leakage, build_position_projection_labels


FORBIDDEN_TERMS = {
    "buy",
    "sell",
    "hold",
    "open",
    "close",
    "reverse",
    "order_quantity",
    "order_type",
    "route",
    "broker_order_id",
    "option_contract",
    "option_symbol",
    "strike",
    "dte",
    "delta",
    "gamma",
    "theta",
    "vega",
    "final_action",
    "execution_instruction",
    "future_fill",
    "realized_pnl",
}


class PositionProjectionModelTests(unittest.TestCase):
    def test_projects_target_exposure_using_pending_adjusted_effective_exposure(self) -> None:
        output = generate_rows([_base_row()])[0]
        vector = output["position_projection_vector"]
        diagnostics = output["position_projection_diagnostics"]

        self.assertGreater(vector["6_target_exposure_score_390min"], 0.0)
        self.assertAlmostEqual(diagnostics["effective_current_exposure_score"], 0.15)
        self.assertAlmostEqual(
            vector["6_position_gap_score_390min"],
            round(vector["6_target_exposure_score_390min"] - 0.15, 6),
        )
        self.assertEqual(vector["6_dominant_projection_horizon"], "390min")
        self.assertNotIn("buy", vector["6_horizon_resolution_reason_codes"][0])
        assert_no_label_leakage(output)
        self.assert_no_forbidden_terms(output)

    def test_gap_aware_cost_does_not_penalize_aligned_position_heavily(self) -> None:
        first = generate_rows([_base_row(current_position_state={"current_position_exposure_score": 0.0})])[0]
        target = first["6_target_exposure_score_390min"]
        aligned = generate_rows(
            [
                _base_row(
                    current_position_state={"current_position_exposure_score": target},
                    pending_position_state={"pending_exposure_size": 0.0, "pending_order_fill_probability_estimate": 0.0},
                    position_level_friction={"spread_cost_estimate": 1.0, "slippage_cost_estimate": 1.0, "turnover_cost_estimate": 1.0},
                )
            ]
        )[0]

        self.assertAlmostEqual(aligned["6_position_gap_magnitude_score_390min"], 0.0, places=5)
        self.assertAlmostEqual(aligned["6_cost_to_adjust_position_score_390min"], 0.0, places=5)
        self.assertGreater(aligned["6_current_position_alignment_score_390min"], 0.99)

    def test_policy_and_risk_can_compress_projection_without_action_language(self) -> None:
        output = generate_rows(
            [
                _base_row(
                    risk_budget_state={"kill_switch_state": "active", "risk_budget_available_score": 0.0},
                    policy_gate_state={"allow_new_exposure": "false"},
                )
            ]
        )[0]

        self.assertEqual(output["6_target_exposure_score_390min"], 0.0)
        self.assertEqual(output["6_risk_budget_fit_score_390min"], 0.0)
        self.assertIn(
            "risk_budget_compression",
            output["position_projection_diagnostics"]["horizon_projections"]["390min"]["reason_codes"],
        )
        self.assert_no_forbidden_terms(output)

    def test_labels_are_offline_and_join_by_vector_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_position_projection_labels(
            [output],
            [
                {
                    "position_projection_vector_ref": output["position_projection_vector_ref"],
                    "realized_position_utility_390min": 0.12,
                    "realized_risk_budget_breach_390min": False,
                    "candidate_exposure_utility_curve_390min": [{"exposure": 0.25, "utility": 0.12}],
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertAlmostEqual(labels[0]["realized_position_utility_390min"], 0.12)
        self.assertNotIn("realized_position_utility_390min", output)

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
        "current_position_state_ref": "current_fixture",
        "pending_position_state_ref": "pending_fixture",
        "alpha_confidence_vector": {
            "5_alpha_direction_score_390min": 0.80,
            "5_alpha_strength_score_390min": 0.70,
            "5_expected_return_score_390min": 0.06,
            "5_alpha_confidence_score_390min": 0.90,
            "5_signal_reliability_score_390min": 0.85,
            "5_path_quality_score_390min": 0.80,
            "5_reversal_risk_score_390min": 0.15,
            "5_drawdown_risk_score_390min": 0.20,
            "5_alpha_tradability_score_390min": 0.90,
        },
        "current_position_state": {"current_position_exposure_score": 0.10},
        "pending_position_state": {"pending_exposure_size": 0.10, "pending_order_fill_probability_estimate": 0.50},
        "position_level_friction": {
            "spread_cost_estimate": 0.02,
            "slippage_cost_estimate": 0.03,
            "fee_cost_estimate": 0.01,
            "turnover_cost_estimate": 0.02,
            "liquidity_capacity_score": 0.90,
        },
        "portfolio_exposure_state": {"correlation_concentration_score": 0.20, "sector_exposure_limit": 0.80},
        "risk_budget_state": {"risk_budget_available_score": 0.90, "single_name_exposure_limit": 0.80},
        "policy_gate_state": {},
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()

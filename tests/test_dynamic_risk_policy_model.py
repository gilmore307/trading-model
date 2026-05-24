from __future__ import annotations

import unittest

from models.model_06_dynamic_risk_policy import generate_rows


class DynamicRiskPolicyModelTests(unittest.TestCase):
    def test_global_minute_policy_row_does_not_require_target_candidate(self) -> None:
        rows = generate_rows(
            [
                {
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "market_context_state": {
                        "1_market_risk_stress_score": 0.35,
                        "1_market_liquidity_support_score": 0.65,
                    },
                    "systemic_event_risk_state": {"systemic_event_risk_score": 0.25},
                    "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.75},
                    "account_capacity_state": {"cash_capacity_score": 0.80},
                }
            ]
        )

        self.assertEqual(rows[0]["policy_scope"], "global")
        self.assertEqual(rows[0]["policy_scope_id"], "global")
        self.assertIsNone(rows[0]["target_candidate_id"])
        self.assertTrue(rows[0]["dynamic_risk_policy_diagnostics"]["minute_level_training_row"])
        self.assertIn("6_resolved_dynamic_risk_budget_score", rows[0])

    def test_target_candidate_scope_remains_supported(self) -> None:
        rows = generate_rows(
            [
                {
                    "available_time": "2026-05-07T10:30:00-04:00",
                    "target_candidate_id": "anon_target_001",
                    "alpha_confidence_vector": {
                        "5_alpha_confidence_score_1W": 0.85,
                        "5_path_quality_score_1W": 0.75,
                    },
                }
            ]
        )

        self.assertEqual(rows[0]["policy_scope"], "target_candidate")
        self.assertEqual(rows[0]["policy_scope_id"], "anon_target_001")
        self.assertEqual(rows[0]["target_candidate_id"], "anon_target_001")
        self.assertFalse(rows[0]["dynamic_risk_policy_diagnostics"]["minute_level_training_row"])


if __name__ == "__main__":
    unittest.main()

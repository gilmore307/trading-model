from __future__ import annotations

import unittest

from models.model_04_event_failure_risk.generator import generate_rows


class EventFailureRiskModelTests(unittest.TestCase):
    def test_reviewed_session_gap_risk_is_emitted_and_can_condition_alpha(self) -> None:
        row = {
            "available_time": "2016-01-08T15:55:00-05:00",
            "tradeable_time": "2016-01-08T15:55:00-05:00",
            "target_candidate_id": "anon_aapl",
            "event_strategy_failure_gate": {
                "agent_review_decision": "accept_layer_04_event_failure_risk_scope",
                "strategy_failure_effect_score_1W": 0.35,
                "path_risk_amplifier_score_1W": 0.20,
                "session_gap_risk_score_1W": 0.90,
                "evidence_quality_score_1W": 0.95,
                "applicability_confidence_score_1W": 0.90,
            },
            "market_context_state": {"1_state_quality_score": 0.90},
            "sector_context_state": {"2_state_quality_score": 0.90},
            "target_context_state": {"3_state_quality_score": 0.90},
        }

        output = generate_rows([row])[0]

        self.assertGreater(output["4_event_session_gap_risk_score_1W"], 0.80)
        self.assertIn(
            "event_session_gap_risk",
            output["event_failure_risk_diagnostics"]["horizon_reason_codes"]["1W"],
        )
        self.assertEqual(output["4_resolved_event_failure_risk_status"], "alpha_conditioning_required")

    def test_unreviewed_rows_do_not_emit_session_gap_risk(self) -> None:
        row = {
            "available_time": "2016-01-08T15:55:00-05:00",
            "target_candidate_id": "anon_aapl",
            "event_strategy_failure_gate": {
                "gate_status": "not_present",
                "session_gap_risk_score_1W": 1.0,
            },
        }

        output = generate_rows([row])[0]

        self.assertEqual(output["4_event_session_gap_risk_score_1W"], 0.0)
        self.assertEqual(output["4_resolved_event_failure_risk_status"], "no_reviewed_event_failure_risk")


if __name__ == "__main__":
    unittest.main()

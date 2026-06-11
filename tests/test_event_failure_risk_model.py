from __future__ import annotations

import unittest

from models.model_04_event_failure_risk.generator import generate_rows
from models.model_04_event_failure_risk.m06_residual_event_governance_focus_pool_inputs import build_layer4_focus_pool_input_rows


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

    def test_m06_residual_event_governance_focus_pool_contract_emits_response_without_event_alpha(self) -> None:
        row = {
            "available_time": "2022-01-14T16:00:00-05:00",
            "target_candidate_id": "m06_residual_event_governance_replay_ed_fixture",
            "m06_residual_event_governance_contract": {
                "contract_owner": "model_06_residual_event_governance",
                "production_route_decision": "approve_focus_pool_entry_risk_control_only",
                "focus_pool_status": "accepted_temporal_attention_focus_pool",
                "accepted_event_families": ["cpi_inflation_release"],
                "selected_window_label": "event_to_plus_3",
                "6_event_presence_score_1D": 0.333333,
                "6_event_timing_proximity_score_1D": 0.80,
                "6_event_intensity_score_1D": 0.75,
                "6_event_gap_risk_score_1D": 0.25,
                "6_event_reversal_risk_score_1D": 0.35,
                "6_event_direction_bias_score_1D": -0.20,
            },
        }

        output = generate_rows([row])[0]

        self.assertGreater(output["4_event_response_strength_score_1D"], 0.0)
        self.assertLess(output["4_event_response_direction_score_1D"], 0.0)
        self.assertGreater(output["4_event_strategy_failure_risk_score_1D"], 0.0)
        self.assertNotIn("event_alpha", output["event_failure_risk_vector"])
        self.assertIn(
            "m06_residual_event_governance_event_parameters_frozen",
            output["event_failure_risk_diagnostics"]["horizon_reason_codes"]["1D"],
        )

    def test_m06_residual_event_governance_focus_pool_input_builder_excludes_rejected_families(self) -> None:
        gate_rows = [
            {
                "family_key": "cpi_inflation_release",
                "production_route_decision": "approve_focus_pool_entry_risk_control_only",
                "focus_pool_status": "accepted_temporal_attention_focus_pool",
            },
            {
                "family_key": "option_derivatives_abnormality",
                "production_route_decision": "reject_current_definition_needs_rework",
                "focus_pool_status": "rejected_from_temporal_attention_focus_pool",
            },
        ]
        replay_rows = [
            {
                "decision_id": "ed_accepted",
                "replay_time_pointer": "2022-01-14T16:00:00-05:00",
                "event_context_vector_ref": "ecv_accepted",
                "visible_event_families": ["cpi_inflation_release", "option_derivatives_abnormality"],
                "visible_event_ids": ["cpi_inflation_release_20220112", "option_derivatives_abnormality_20220114"],
                "visible_event_window_policies": ["calibrated_impact_window", "calibrated_impact_window"],
                "6_event_presence_score_1D": 0.666667,
                "6_event_timing_proximity_score_1D": 0.5,
            },
            {
                "decision_id": "ed_rejected_only",
                "replay_time_pointer": "2022-01-15T16:00:00-05:00",
                "visible_event_families": ["option_derivatives_abnormality"],
            },
        ]

        rows = build_layer4_focus_pool_input_rows(replay_overlay_rows=replay_rows, gate_matrix_rows=gate_rows)

        self.assertEqual(len(rows), 1)
        contract = rows[0]["m06_residual_event_governance_contract"]
        self.assertEqual(contract["accepted_event_families"], ["cpi_inflation_release"])
        self.assertEqual(contract["visible_event_ids"], ["cpi_inflation_release_20220112"])
        self.assertNotIn("option_derivatives_abnormality", contract["accepted_event_families"])
        self.assertNotIn("option_derivatives_abnormality_20220114", contract["visible_event_ids"])


if __name__ == "__main__":
    unittest.main()

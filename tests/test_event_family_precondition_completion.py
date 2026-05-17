from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_family_precondition_completion import (
    build_event_family_precondition_completion,
    write_precondition_artifacts,
)


class EventFamilyPreconditionCompletionTests(unittest.TestCase):
    def test_builds_packet_for_every_family_and_preserves_safety(self) -> None:
        completion = build_event_family_precondition_completion(generated_at_utc="2026-05-16T22:00:00+00:00")
        payload = completion.to_dict()

        self.assertEqual(payload["contract_type"], "event_family_precondition_completion_v1")
        self.assertEqual(payload["summary"]["family_count"], 29)
        self.assertEqual(payload["summary"]["packet_status_counts"]["packet_spec_completed_pending_empirical_evidence"], 26)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["sql_destructive_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_packets_fill_missing_packet_blocker_but_keep_empirical_gates(self) -> None:
        completion = build_event_family_precondition_completion(generated_at_utc="2026-05-16T22:00:00+00:00")
        for packet in completion.packets:
            self.assertNotIn("missing_family_packet", packet.remaining_blocker_codes)
            self.assertIn("empirical_association_study_required", packet.remaining_blocker_codes)
            self.assertTrue(packet.canonical_source_precedence)
            self.assertTrue(packet.point_in_time_clock_rules)
            self.assertTrue(packet.baseline_requirements)
            self.assertTrue(packet.matched_control_design)

    def test_special_evidence_gates_are_explicit(self) -> None:
        completion = build_event_family_precondition_completion(generated_at_utc="2026-05-16T22:00:00+00:00")
        by_family = {packet.family_key: packet for packet in completion.packets}

        self.assertIn("fuller_te_expectation_history_required", by_family["cpi_inflation_release"].remaining_blocker_codes)
        self.assertIn("pit_expectation_or_comparable_baseline_required", by_family["earnings_guidance_result_metrics"].remaining_blocker_codes)
        self.assertIn("residual_over_base_state_required", by_family["price_action_pattern"].remaining_blocker_codes)
        self.assertIn("liquidity_depth_evidence_required", by_family["microstructure_liquidity_disruption"].remaining_blocker_codes)
        self.assertIn("revised_abnormality_definition_required", by_family["option_derivatives_abnormality"].remaining_blocker_codes)

    def test_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "preconditions"
            completion = build_event_family_precondition_completion(generated_at_utc="2026-05-16T22:00:00+00:00")
            write_precondition_artifacts(completion, output_dir)

            payload_path = output_dir / "event_family_precondition_completion.json"
            summary_path = output_dir / "event_family_precondition_completion_summary.json"
            packets_path = output_dir / "event_family_scouting_packets.jsonl"
            requirements_path = output_dir / "event_family_evidence_requirements.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(packets_path.exists())
            self.assertTrue(requirements_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["final_conclusion"], "withheld_until_all_required_empirical_association_studies_exist")
            self.assertIn("equity_offering_dilution", requirements_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

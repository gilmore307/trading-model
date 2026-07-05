from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from models.model_03_event_state.event_governance.event_model_acceptance import build_event_model_acceptance_report, write_report_file


class EventModelAcceptanceTests(unittest.TestCase):
    def test_acceptance_accepts_m03_event_effect_governance_and_blocks_alpha_activation(self) -> None:
        report = build_event_model_acceptance_report(generated_at_utc="2026-05-16T00:00:00+00:00")
        row = report.summary_row()

        self.assertEqual(row["contract_type"], "event_model_acceptance_report")
        self.assertEqual(row["architecture_status"], "accepted_m03_event_effect_model_governance")
        self.assertIn("event_effect_model_distribution_and_gate_channels", row["accepted_build_boundary"])
        self.assertIn("component_owned_block_cap_reduce_flatten_controls", row["accepted_build_boundary"])
        self.assertIn("trading-model/docs/12_model_03_event_state.md", row["source_documents"])
        self.assertIn("signed_earnings_guidance_alpha_without_pit_expectation_baselines", row["rejected_routes"])
        self.assertFalse(row["model_activation_performed"])
        self.assertFalse(row["broker_execution_performed"])
        self.assertFalse(row["artifact_deletion_performed"])

        families = {item["family_key"]: item for item in row["family_statuses"]}
        self.assertEqual(families["earnings_guidance_event_family"]["status"], "scouting_direction_neutral_context_only")
        self.assertIn("missing_pit_revenue_consensus_baseline", families["earnings_guidance_event_family"]["blocker_codes"])
        governor = families["event_effect_model_governance_structure"]
        self.assertEqual(governor["status"], "accepted_architecture")
        self.assertIn("model_03_event_state_event_inputs", governor["next_evidence_gate"])
        self.assertIn("model_03_event_state", governor["next_evidence_gate"])
        self.assertNotIn("source_08", governor["next_evidence_gate"])
        self.assertNotIn("feature_08", governor["next_evidence_gate"])
        self.assertNotIn("model_" + "08_" + "event_effect_model", governor["next_evidence_gate"])

        self.assertIn("M03-event-dependent outputs", row["downstream_regeneration_policy"])
        self.assertIn("model_03_event_state", row["downstream_regeneration_policy"])
        self.assertNotIn("source_08", row["downstream_regeneration_policy"])
        self.assertNotIn("feature_08", row["downstream_regeneration_policy"])
        self.assertNotIn("model_" + "08_" + "event_effect_model", row["downstream_regeneration_policy"])

    def test_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = Path(raw_tmp) / "acceptance.json"
            report = build_event_model_acceptance_report(generated_at_utc="2026-05-16T00:00:00+00:00")
            write_report_file(report, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_model_acceptance_report")


if __name__ == "__main__":
    unittest.main()

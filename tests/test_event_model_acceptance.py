from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from models.model_06_residual_event_governance.event_model_acceptance import build_event_model_acceptance_report, write_report_file


class EventModelAcceptanceTests(unittest.TestCase):
    def test_acceptance_accepts_risk_governor_and_blocks_alpha_activation(self) -> None:
        report = build_event_model_acceptance_report(generated_at_utc="2026-05-16T00:00:00+00:00")
        row = report.summary_row()

        self.assertEqual(row["contract_type"], "event_model_acceptance_report")
        self.assertEqual(row["architecture_status"], "accepted_bounded_event_risk_governor")
        self.assertIn("risk_governor_intervention_review_block_cap_reduce_flatten_hints", row["accepted_build_boundary"])
        self.assertIn("base_layers_1_9_guidance_preserved_side_by_side_with_event_adjusted_guidance", row["accepted_build_boundary"])
        self.assertIn("trading-model/docs/15_model_06_residual_event_governance.md", row["source_documents"])
        self.assertIn("signed_earnings_guidance_alpha_without_pit_expectation_baselines", row["rejected_routes"])
        self.assertFalse(row["model_activation_performed"])
        self.assertFalse(row["broker_execution_performed"])
        self.assertFalse(row["artifact_deletion_performed"])

        families = {item["family_key"]: item for item in row["family_statuses"]}
        self.assertEqual(families["earnings_guidance_event_family"]["status"], "scouting_direction_neutral_context_only")
        self.assertIn("missing_pit_revenue_consensus_baseline", families["earnings_guidance_event_family"]["blocker_codes"])
        governor = families["event_risk_governor_structure"]
        self.assertEqual(governor["status"], "accepted_architecture")
        self.assertIn("m06_residual_event_governance_data_acquisition", governor["next_evidence_gate"])
        self.assertIn("m06_residual_event_governance_feature_generation", governor["next_evidence_gate"])
        self.assertIn("model_06_residual_event_governance", governor["next_evidence_gate"])
        self.assertNotIn("source_08", governor["next_evidence_gate"])
        self.assertNotIn("feature_08", governor["next_evidence_gate"])
        self.assertNotIn("model_" + "08_" + "event_risk_governor", governor["next_evidence_gate"])

        self.assertIn("m06_residual_event_governance_data_acquisition", row["downstream_regeneration_policy"])
        self.assertIn("m06_residual_event_governance_feature_generation", row["downstream_regeneration_policy"])
        self.assertIn("model_06_residual_event_governance", row["downstream_regeneration_policy"])
        self.assertNotIn("source_08", row["downstream_regeneration_policy"])
        self.assertNotIn("feature_08", row["downstream_regeneration_policy"])
        self.assertNotIn("model_" + "08_" + "event_risk_governor", row["downstream_regeneration_policy"])

    def test_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = Path(raw_tmp) / "acceptance.json"
            report = build_event_model_acceptance_report(generated_at_utc="2026-05-16T00:00:00+00:00")
            write_report_file(report, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_model_acceptance_report")


if __name__ == "__main__":
    unittest.main()

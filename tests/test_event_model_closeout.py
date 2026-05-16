from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from models.model_08_event_risk_governor.event_model_closeout import build_event_model_closeout_report, write_report_file


class EventModelCloseoutTests(unittest.TestCase):
    def test_closeout_accepts_risk_governor_and_blocks_alpha_activation(self) -> None:
        report = build_event_model_closeout_report(generated_at_utc="2026-05-16T00:00:00+00:00")
        row = report.summary_row()

        self.assertEqual(row["contract_type"], "event_model_closeout_report_v1")
        self.assertEqual(row["architecture_status"], "accepted_bounded_event_risk_governor")
        self.assertIn("risk_governor_intervention_review_block_cap_reduce_flatten_hints", row["accepted_build_boundary"])
        self.assertIn("signed_earnings_guidance_alpha_without_pit_expectation_baselines", row["rejected_routes"])
        self.assertFalse(row["model_activation_performed"])
        self.assertFalse(row["broker_execution_performed"])
        self.assertFalse(row["artifact_deletion_performed"])

        families = {item["family_key"]: item for item in row["family_statuses"]}
        self.assertEqual(families["earnings_guidance_event_family"]["status"], "scouting_direction_neutral_context_only")
        self.assertIn("missing_pit_revenue_consensus_baseline", families["earnings_guidance_event_family"]["blocker_codes"])
        self.assertEqual(families["event_risk_governor_structure"]["status"], "accepted_architecture")

    def test_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = Path(raw_tmp) / "closeout.json"
            report = build_event_model_closeout_report(generated_at_utc="2026-05-16T00:00:00+00:00")
            write_report_file(report, path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_model_closeout_report_v1")


if __name__ == "__main__":
    unittest.main()

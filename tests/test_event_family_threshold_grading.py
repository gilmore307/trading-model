from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_family_threshold_grading import (
    build_event_family_threshold_grading,
    write_event_family_threshold_grading_artifacts,
)


class EventFamilyThresholdGradingTests(unittest.TestCase):
    def test_deletes_no_clear_families_from_threshold_queue_only(self) -> None:
        grading = build_event_family_threshold_grading(generated_at_utc="2026-05-17T03:00:00+00:00")
        by_family = {row.family_key: row for row in grading.family_rows}

        self.assertTrue(by_family["mna_transaction"].delete_from_threshold_queue)
        self.assertEqual(by_family["mna_transaction"].deletion_scope, "threshold_queue_only")
        self.assertTrue(by_family["product_launch_or_failure"].delete_from_threshold_queue)
        self.assertTrue(by_family["sector_demand_shock"].delete_from_threshold_queue)
        self.assertFalse(by_family["earnings_call_narrative_residual"].delete_from_threshold_queue)

    def test_summary_active_and_deleted_sets(self) -> None:
        grading = build_event_family_threshold_grading(generated_at_utc="2026-05-17T03:00:00+00:00")
        summary = grading.summary

        self.assertIn("cpi_inflation_release", summary["active_threshold_universe"])
        self.assertIn("earnings_guidance_scheduled_shell", summary["active_threshold_universe"])
        self.assertIn("equity_offering_dilution", summary["active_threshold_universe"])
        self.assertIn("mna_transaction", summary["deleted_from_threshold_queue"])
        self.assertIn("option_derivatives_abnormality", summary["deleted_from_threshold_queue"])
        self.assertEqual(summary["provider_calls"], 0)
        self.assertFalse(summary["artifact_deletion_performed"])

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "grading"
            grading = build_event_family_threshold_grading(generated_at_utc="2026-05-17T03:00:00+00:00")
            write_event_family_threshold_grading_artifacts(grading, output_dir)

            payload_path = output_dir / "event_family_threshold_grading.json"
            csv_path = output_dir / "event_family_threshold_grading.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(csv_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_family_threshold_grading_v1")
            self.assertIn("delete_from_threshold_queue", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

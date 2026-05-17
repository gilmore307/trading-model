from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from event_family_fixtures import build_event_family_fixture

from models.model_09_event_risk_governor.event_family_remaining_acceptance import (
    build_event_family_remaining_acceptance,
    write_acceptance_artifacts,
)


class EventFamilyRemainingAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.fixture = build_event_family_fixture(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_acceptance_accounts_for_all_catalog_families_and_preserves_safety(self) -> None:
        batch = build_event_family_remaining_acceptance(catalog_path=self.fixture.catalog_path, generated_at_utc="2026-05-16T16:00:00+00:00")
        payload = batch.to_dict()

        self.assertEqual(payload["contract_type"], "event_family_remaining_acceptance_v1")
        self.assertEqual(payload["summary"]["family_count"], 29)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_no_family_is_promoted_to_directional_alpha(self) -> None:
        batch = build_event_family_remaining_acceptance(catalog_path=self.fixture.catalog_path, generated_at_utc="2026-05-16T16:00:00+00:00")
        for row in batch.family_rows:
            self.assertTrue(row.alpha_promotion_status.startswith("alpha_blocked") or row.alpha_promotion_status == "alpha_not_applicable_execution_risk_family")

    def test_cpi_and_option_dispositions_are_conservative(self) -> None:
        batch = build_event_family_remaining_acceptance(catalog_path=self.fixture.catalog_path, generated_at_utc="2026-05-16T16:00:00+00:00")
        by_family = {row.family_key: row for row in batch.family_rows}

        cpi = by_family["cpi_inflation_release"]
        self.assertEqual(cpi.acceptance_status, "risk_only_candidate_temporary_evidence")
        self.assertEqual(cpi.risk_feature_status, "risk_candidate_macro_surprise_control")
        self.assertIn("canonical_te_expectation_history_needed", cpi.blocker_codes)

        option = by_family["option_derivatives_abnormality"]
        self.assertEqual(option.acceptance_status, "deferred_low_signal")
        self.assertEqual(option.next_action_class, "defer_until_definition_changes")

    def test_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "acceptance"
            batch = build_event_family_remaining_acceptance(catalog_path=self.fixture.catalog_path, generated_at_utc="2026-05-16T16:00:00+00:00")
            write_acceptance_artifacts(batch, output_dir)

            payload_path = output_dir / "event_family_remaining_acceptance.json"
            summary_path = output_dir / "event_family_remaining_acceptance_summary.json"
            queue_path = output_dir / "event_family_next_packet_queue.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(queue_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["family_count"], 29)
            self.assertIn("equity_offering_dilution", queue_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

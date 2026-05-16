from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_price_association_readiness import (
    build_event_price_association_readiness_batch,
    write_batch_artifacts,
)


class EventPriceAssociationReadinessTests(unittest.TestCase):
    def test_default_batch_preserves_non_mutating_boundary(self) -> None:
        batch = build_event_price_association_readiness_batch(generated_at_utc="2026-05-16T12:00:00+00:00")
        payload = batch.to_dict()

        self.assertEqual(payload["contract_type"], "event_price_association_readiness_batch_v1")
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])
        self.assertEqual(payload["family_keys"], [
            "equity_offering_dilution",
            "legal_regulatory_investigation",
            "cpi_inflation_release",
            "credit_liquidity_stress",
        ])

    def test_cpi_family_has_local_candidates_and_price_labels_but_stays_underpowered(self) -> None:
        batch = build_event_price_association_readiness_batch(generated_at_utc="2026-05-16T12:00:00+00:00")
        by_family = {row.family_key: row for row in batch.family_readiness}

        self.assertGreater(by_family["cpi_inflation_release"].candidate_event_count, 0)
        self.assertGreater(by_family["cpi_inflation_release"].price_label_count, 0)
        self.assertEqual(
            by_family["cpi_inflation_release"].association_study_status,
            "underpowered_single_month_scouting_only",
        )
        self.assertIn("single_month_only", by_family["cpi_inflation_release"].blocker_codes)

    def test_blocked_families_do_not_claim_association(self) -> None:
        batch = build_event_price_association_readiness_batch(generated_at_utc="2026-05-16T12:00:00+00:00")
        by_family = {row.family_key: row for row in batch.family_readiness}

        self.assertEqual(by_family["equity_offering_dilution"].association_study_status, "blocked_missing_offering_terms_parser")
        self.assertEqual(
            by_family["legal_regulatory_investigation"].association_study_status,
            "blocked_missing_official_source_and_severity_taxonomy",
        )
        self.assertEqual(
            by_family["credit_liquidity_stress"].association_study_status,
            "blocked_missing_stress_event_standard",
        )

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "association"
            batch = build_event_price_association_readiness_batch(generated_at_utc="2026-05-16T12:00:00+00:00")
            write_batch_artifacts(batch, output_dir)

            batch_path = output_dir / "event_price_association_batch.json"
            readiness_path = output_dir / "event_price_association_family_readiness.csv"
            events_path = output_dir / "event_price_association_candidate_events.csv"
            labels_path = output_dir / "event_price_association_price_labels.csv"
            self.assertTrue(batch_path.exists())
            self.assertTrue(readiness_path.exists())
            self.assertTrue(events_path.exists())
            self.assertTrue(labels_path.exists())
            payload = json.loads(batch_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_price_association_readiness_batch_v1")
            self.assertIn("cpi_inflation_release", readiness_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

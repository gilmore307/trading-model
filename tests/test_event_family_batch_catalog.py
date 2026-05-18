from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_family_batch_catalog import (
    build_event_family_batch_catalog,
    write_catalog_artifacts,
)


class EventFamilyBatchCatalogTests(unittest.TestCase):
    def test_catalog_is_fine_grained_and_non_mutating(self) -> None:
        catalog = build_event_family_batch_catalog(root=Path("."), generated_at_utc="2026-05-16T12:00:00+00:00")
        row = catalog.to_dict()

        self.assertEqual(row["contract_type"], "event_family_batch_catalog_v1")
        self.assertEqual(row["provider_calls"], 0)
        self.assertFalse(row["model_activation_performed"])
        self.assertFalse(row["broker_execution_performed"])
        self.assertFalse(row["account_mutation_performed"])
        self.assertFalse(row["artifact_deletion_performed"])

        family_keys = {candidate["family_key"] for candidate in row["candidates"]}
        self.assertIn("earnings_guidance_scheduled_shell", family_keys)
        self.assertIn("equity_offering_dilution", family_keys)
        self.assertIn("legal_regulatory_investigation", family_keys)
        self.assertIn("cpi_inflation_release", family_keys)
        self.assertIn("option_derivatives_abnormality", family_keys)

        forbidden_broad_families = {"symbol_news", "sector_news", "macro_news", "sec_filing", "earnings_guidance"}
        self.assertTrue(forbidden_broad_families.isdisjoint(family_keys))
        self.assertGreaterEqual(len(family_keys), 25)

    def test_summary_counts_batch_priorities_and_statuses(self) -> None:
        catalog = build_event_family_batch_catalog(root=Path("."), generated_at_utc="2026-05-16T12:00:00+00:00")
        summary = catalog.summary

        self.assertEqual(summary["contract_type"], "event_family_batch_summary_v1")
        self.assertEqual(summary["candidate_count"], len(catalog.candidates))
        self.assertGreater(summary["priority_counts"]["high"], 5)
        self.assertIn("scouting", summary["family_status_counts"])
        self.assertIn("proposed", summary["family_status_counts"])
        self.assertIn("deferred_low_signal", summary["family_status_counts"])

    def test_writes_json_and_csv_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "batch"
            catalog = build_event_family_batch_catalog(root=Path("."), generated_at_utc="2026-05-16T12:00:00+00:00")
            write_catalog_artifacts(catalog, output_dir)

            catalog_path = output_dir / "event_family_batch_catalog.json"
            summary_path = output_dir / "event_family_batch_summary.json"
            queue_path = output_dir / "event_family_batch_queue.csv"
            packets_path = output_dir / "event_family_first_pass_packets.jsonl"
            blockers_path = output_dir / "event_family_blocker_queue.csv"
            self.assertTrue(catalog_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(queue_path.exists())
            self.assertTrue(packets_path.exists())
            self.assertTrue(blockers_path.exists())
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contract_type"], "event_family_batch_catalog_v1")
            self.assertIn("equity_offering_dilution", queue_path.read_text(encoding="utf-8"))
            self.assertIn("event_family_first_pass_packet_v1", packets_path.read_text(encoding="utf-8"))
            self.assertIn("missing_family_packet", blockers_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

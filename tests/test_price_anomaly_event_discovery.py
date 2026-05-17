from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_09_event_risk_governor.price_anomaly_event_discovery import (
    build_price_anomaly_event_discovery,
    write_price_anomaly_event_discovery_artifacts,
)


class PriceAnomalyEventDiscoveryTests(unittest.TestCase):
    def test_builds_reverse_discovery_with_safety_flags(self) -> None:
        discovery = build_price_anomaly_event_discovery(generated_at_utc="2026-05-17T03:00:00+00:00")
        payload = discovery.to_dict()

        self.assertEqual(payload["contract_type"], "price_anomaly_event_discovery_v1")
        self.assertGreater(payload["summary"]["anomaly_count"], 0)
        self.assertGreater(payload["summary"]["enriched_family_count"], 0)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_reverse_candidates_are_explicit(self) -> None:
        discovery = build_price_anomaly_event_discovery(generated_at_utc="2026-05-17T03:00:00+00:00")
        statuses = {row.threshold_discovery_status for row in discovery.enrichment_rows}

        self.assertIn("reverse_discovery_candidate", statuses)
        self.assertTrue(discovery.summary["candidate_common_event_families"])

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "reverse"
            discovery = build_price_anomaly_event_discovery(generated_at_utc="2026-05-17T03:00:00+00:00")
            write_price_anomaly_event_discovery_artifacts(discovery, output_dir)

            payload_path = output_dir / "price_anomaly_event_discovery.json"
            enrichment_path = output_dir / "price_anomaly_event_family_enrichment.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(enrichment_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["provider_calls"], 0)
            self.assertIn("threshold_discovery_status", enrichment_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

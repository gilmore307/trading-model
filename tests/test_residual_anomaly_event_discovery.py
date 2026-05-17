from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_09_event_risk_governor.residual_anomaly_event_discovery import (
    build_residual_anomaly_event_discovery,
    write_residual_anomaly_event_discovery_artifacts,
)


class ResidualAnomalyEventDiscoveryTests(unittest.TestCase):
    def test_builds_from_layer_seven_evaluation_labels_with_safety_flags(self) -> None:
        discovery = build_residual_anomaly_event_discovery(generated_at_utc="2026-05-17T03:30:00+00:00")
        payload = discovery.to_dict()

        self.assertEqual(payload["contract_type"], "residual_anomaly_event_discovery_v1")
        self.assertGreater(payload["summary"]["residual_anomaly_count"], 0)
        self.assertGreater(payload["summary"]["enriched_family_count"], 0)
        self.assertEqual(payload["summary"]["service_integration_status"], "registered_callable_artifact_builder_only_no_daemon_start")
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["service_daemon_started"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_current_fixture_does_not_auto_promote_without_controls(self) -> None:
        discovery = build_residual_anomaly_event_discovery(generated_at_utc="2026-05-17T03:30:00+00:00")

        self.assertEqual(discovery.summary["control_label_status"], "missing_non_residual_control_labels")
        self.assertEqual(discovery.summary["strategy_promotion_review_candidates"], [])
        self.assertEqual(discovery.summary["promotion_review_packet_count"], 0)
        self.assertTrue(
            any(row.observation_pool_recommendation == "research_only_needs_non_residual_controls" for row in discovery.enrichment_rows)
        )

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "residual"
            discovery = build_residual_anomaly_event_discovery(generated_at_utc="2026-05-17T03:30:00+00:00")
            write_residual_anomaly_event_discovery_artifacts(discovery, output_dir)

            payload_path = output_dir / "residual_anomaly_event_discovery.json"
            enrichment_path = output_dir / "residual_anomaly_event_family_enrichment.csv"
            packet_path = output_dir / "event_family_strategy_promotion_review_packets.jsonl"
            self.assertTrue(payload_path.exists())
            self.assertTrue(enrichment_path.exists())
            self.assertTrue(packet_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["provider_calls"], 0)
            self.assertIn("observation_pool_recommendation", enrichment_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

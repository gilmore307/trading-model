from __future__ import annotations

import json
import tempfile
import unittest
import csv
from datetime import date, timedelta
from pathlib import Path

from models.model_06_residual_event_governance.price_anomaly_event_discovery import (
    build_price_anomaly_event_discovery,
    write_price_anomaly_event_discovery_artifacts,
)


class PriceAnomalyEventDiscoveryTests(unittest.TestCase):
    def _fixture_roots(self, raw_tmp: str) -> tuple[Path, Path]:
        root = Path(raw_tmp)
        bar_path = root / "alpaca_bars" / "AAPL" / "2016-01" / "runs" / "run" / "saved" / "equity_bar.csv"
        bar_path.parent.mkdir(parents=True)
        event_path = (
            root
            / "sources"
            / "trading_economics_calendar_web"
            / "2016-01"
            / "runs"
            / "run"
            / "saved"
            / "trading_economics_calendar_event.csv"
        )
        event_path.parent.mkdir(parents=True)
        start = date(2016, 1, 1)
        with bar_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "bar_open", "bar_high", "bar_low", "bar_close"])
            writer.writeheader()
            for index in range(22):
                day = start + timedelta(days=index)
                close = 100.0 + index
                writer.writerow(
                    {
                        "timestamp": f"{day.isoformat()}T16:00:00+00:00",
                        "bar_open": close - 0.5,
                        "bar_high": close + 1.0,
                        "bar_low": close - 1.0,
                        "bar_close": close,
                    }
                )
        with event_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_time", "event", "source_event_type"])
            writer.writeheader()
            for index in range(1, 22):
                day = start + timedelta(days=index)
                writer.writerow(
                    {
                        "event_time": f"{day.isoformat()}T08:30:00+00:00",
                        "event": "CPI inflation release",
                        "source_event_type": "macro_data",
                    }
                )
        return root / "alpaca_bars", root / "sources"

    def test_builds_reverse_discovery_with_safety_flags(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            bar_root, source_root = self._fixture_roots(raw_tmp)
            discovery = build_price_anomaly_event_discovery(
                bar_root=bar_root,
                source_root=source_root,
                anomaly_z_threshold=-999.0,
                generated_at_utc="2026-05-17T03:00:00+00:00",
            )
            payload = discovery.to_dict()

        self.assertEqual(payload["contract_type"], "price_anomaly_event_discovery")
        self.assertGreater(payload["summary"]["anomaly_count"], 0)
        self.assertGreater(payload["summary"]["enriched_family_count"], 0)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_reverse_candidates_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            bar_root, source_root = self._fixture_roots(raw_tmp)
            discovery = build_price_anomaly_event_discovery(
                bar_root=bar_root,
                source_root=source_root,
                anomaly_z_threshold=-999.0,
                generated_at_utc="2026-05-17T03:00:00+00:00",
            )
        statuses = {row.threshold_discovery_status for row in discovery.enrichment_rows}

        self.assertIn("reverse_discovery_candidate", statuses)
        self.assertTrue(discovery.summary["candidate_common_event_families"])

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            bar_root, source_root = self._fixture_roots(raw_tmp)
            output_dir = Path(raw_tmp) / "reverse"
            discovery = build_price_anomaly_event_discovery(
                bar_root=bar_root,
                source_root=source_root,
                anomaly_z_threshold=-999.0,
                generated_at_utc="2026-05-17T03:00:00+00:00",
            )
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

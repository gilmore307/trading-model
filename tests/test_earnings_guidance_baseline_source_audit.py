from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_baseline_source_audit import (
    BaselineSourceAuditInputs,
    run_baseline_source_audit,
)


class EarningsGuidanceBaselineSourceAuditTests(unittest.TestCase):
    def _write_event(self, root: Path, event_date: str = "2025-10-30") -> Path:
        path = root / "events.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "cal_1", "event_date": event_date})
        return path

    def _write_calendar(self, root: Path, fetched_at: str, raw: dict[str, str]) -> Path:
        run = root / "calendar" / "runs" / "run1"
        saved = run / "saved"
        saved.mkdir(parents=True)
        (run / "request_manifest.json").write_text(json.dumps({"fetched_at_utc": fetched_at}) + "\n", encoding="utf-8")
        path = saved / "release_calendar.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_id", "event_date", "source_url", "raw_summary"])
            writer.writeheader()
            writer.writerow({"event_id": "cal_1", "event_date": "2025-10-30", "source_url": "https://api.nasdaq.com/api/calendar/earnings?date=2025-10-30", "raw_summary": json.dumps(raw)})
        return root / "calendar"

    def test_post_event_calendar_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events = self._write_event(root)
            calroot = self._write_calendar(root, "2026-05-15T15:00:00Z", {"symbol": "XYZ", "epsForecast": "$1.00", "eps": "$1.10", "surprise": "10"})
            report = run_baseline_source_audit(BaselineSourceAuditInputs(events, calroot, root / "out"))
            self.assertEqual(report["eps_forecast_present_event_count"], 1)
            self.assertEqual(report["accepted_pit_baseline_event_count"], 0)
            with (root / "out" / "earnings_guidance_baseline_source_audit_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["pit_acceptance_status"], "rejected_post_event_or_same_day_calendar_snapshot")

    def test_clean_pre_event_eps_snapshot_is_candidate_route_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events = self._write_event(root)
            calroot = self._write_calendar(root, "2025-10-29T15:00:00Z", {"symbol": "XYZ", "epsForecast": "$1.00", "noOfEsts": "4"})
            report = run_baseline_source_audit(BaselineSourceAuditInputs(events, calroot, root / "out"))
            self.assertEqual(report["accepted_pit_baseline_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_baseline_source_audit_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["pit_acceptance_status"], "candidate_future_pit_eps_consensus_route")


if __name__ == "__main__":
    unittest.main()

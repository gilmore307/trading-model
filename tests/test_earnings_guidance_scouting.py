from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_scouting import StudyInputs, load_calendar_events, run_study


class EarningsGuidanceScoutingTests(unittest.TestCase):
    def test_loads_nasdaq_calendar_shells_for_target_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = Path(raw_tmp) / "release_calendar.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "calendar_source", "event_name", "release_time", "event_date", "timezone", "source_url", "raw_summary"])
                writer.writeheader()
                writer.writerow({"event_id": "cal1", "calendar_source": "nasdaq_earnings_calendar", "event_name": "XOM earnings release (Exxon Mobil Corporation)", "release_time": "2026-05-01T00:00:00-04:00", "event_date": "2026-05-01", "timezone": "America/New_York", "source_url": "https://api.nasdaq.com/api/calendar/earnings", "raw_summary": "{}"})
                writer.writerow({"event_id": "cal2", "calendar_source": "nasdaq_earnings_calendar", "event_name": "ZZZZ earnings release (Other)", "release_time": "2026-05-01T00:00:00-04:00", "event_date": "2026-05-01", "timezone": "America/New_York", "source_url": "https://api.nasdaq.com/api/calendar/earnings", "raw_summary": "{}"})
            events = load_calendar_events([path], ["XOM"])
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["symbol"], "XOM")
            self.assertEqual(events[0]["event_phase"], "scheduled_shell")
            self.assertEqual(events[0]["result_fields"], "not_available_from_calendar_shell")

    def test_run_study_separates_earnings_shells_and_verified_non_earnings_controls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            abnormal = tmp / "matched_abnormal_windows.csv"
            control = tmp / "matched_control_windows.csv"
            calendar = tmp / "release_calendar.csv"
            with abnormal.open("w", newline="", encoding="utf-8") as handle:
                fields = ["symbol", "event_date", "direction_hypothesis", "direction_sign", "event_count", "event_abs_fwd_10d", "event_directional_fwd_10d", "event_path_range_10d"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"symbol": "XOM", "event_date": "2026-05-01", "direction_hypothesis": "bullish_activity", "direction_sign": "1", "event_count": "2", "event_abs_fwd_10d": "0.10", "event_directional_fwd_10d": "0.10", "event_path_range_10d": "0.20"})
            with control.open("w", newline="", encoding="utf-8") as handle:
                fields = ["symbol", "event_date", "control_date", "direction_hypothesis", "control_abs_fwd_10d", "control_directional_fwd_10d", "control_path_range_10d"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"symbol": "XOM", "event_date": "2026-05-01", "control_date": "2026-04-24", "direction_hypothesis": "bullish_activity", "control_abs_fwd_10d": "0.04", "control_directional_fwd_10d": "0.04", "control_path_range_10d": "0.10"})
                writer.writerow({"symbol": "XOM", "event_date": "2026-05-01", "control_date": "2026-05-01", "direction_hypothesis": "bullish_activity", "control_abs_fwd_10d": "0.50", "control_directional_fwd_10d": "0.50", "control_path_range_10d": "0.50"})
            with calendar.open("w", newline="", encoding="utf-8") as handle:
                fields = ["event_id", "calendar_source", "event_name", "release_time", "event_date", "timezone", "source_url", "raw_summary"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"event_id": "cal1", "calendar_source": "nasdaq_earnings_calendar", "event_name": "XOM earnings release (Exxon Mobil Corporation)", "release_time": "2026-05-01T00:00:00-04:00", "event_date": "2026-05-01", "timezone": "America/New_York", "source_url": "https://api.nasdaq.com/api/calendar/earnings", "raw_summary": "{}"})
            report = run_study(StudyInputs(abnormal, control, (calendar,), tmp / "out", target_symbols=("XOM",)))
            self.assertEqual(report["canonical_earnings_shell_window_count"], 1)
            with (tmp / "out" / "earnings_guidance_window_pairs.csv").open(newline="", encoding="utf-8") as handle:
                pairs = list(csv.DictReader(handle))
            self.assertEqual(pairs[0]["verified_non_earnings_control_count"], "1")
            self.assertAlmostEqual(float(pairs[0]["delta_abs_fwd_10d"]), 0.06)


if __name__ == "__main__":
    unittest.main()

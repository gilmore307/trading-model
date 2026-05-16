from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_event_alone import EventAloneInputs, run_event_alone_study


class EarningsGuidanceEventAloneTests(unittest.TestCase):
    def test_event_alone_study_pairs_calendar_shell_with_non_earnings_controls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            calendar = tmp / "release_calendar.csv"
            bars = tmp / "equity_bar.csv"
            with calendar.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "calendar_source", "event_name", "release_time", "event_date", "timezone", "source_url", "raw_summary"])
                writer.writeheader()
                writer.writerow({"event_id": "cal1", "calendar_source": "nasdaq_earnings_calendar", "event_name": "XYZ earnings release (XYZ Corp)", "release_time": "2025-10-30T00:00:00-04:00", "event_date": "2025-10-30", "timezone": "America/New_York", "source_url": "https://api.nasdaq.com/api/calendar/earnings", "raw_summary": "{}"})
            with bars.open("w", newline="", encoding="utf-8") as handle:
                fields = ["symbol", "timeframe", "timestamp", "bar_open", "bar_high", "bar_low", "bar_close", "bar_volume", "bar_vwap", "bar_trade_count"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                start = date(2025, 10, 1)
                for idx in range(55):
                    day = start + timedelta(days=idx)
                    close = 100 + idx
                    high = close + (10 if day.isoformat() == "2025-10-31" else 1)
                    low = close - 1
                    writer.writerow({"symbol": "XYZ", "timeframe": "1Day", "timestamp": f"{day.isoformat()}T00:00:00-04:00", "bar_open": close, "bar_high": high, "bar_low": low, "bar_close": close, "bar_volume": 1000, "bar_vwap": close, "bar_trade_count": 10})
            report = run_event_alone_study(EventAloneInputs((calendar,), (bars,), tmp / "out", ("XYZ",)))
            self.assertEqual(report["event_window_count"], 1)
            self.assertGreaterEqual(report["control_window_count"], 1)
            pairs_path = tmp / "out" / "earnings_guidance_event_control_pairs.csv"
            with pairs_path.open(newline="", encoding="utf-8") as handle:
                pairs = list(csv.DictReader(handle))
            self.assertEqual(pairs[0]["symbol"], "XYZ")
            self.assertGreater(float(pairs[0]["event_path_range_1d"]), 0.0)


if __name__ == "__main__":
    unittest.main()

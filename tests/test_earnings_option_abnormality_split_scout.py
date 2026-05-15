from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_option_abnormality_split_scout import EarningsOptionSplitInputs, run_earnings_option_split_scout


class EarningsOptionAbnormalitySplitScoutTests(unittest.TestCase):
    def test_marks_blocked_when_no_verified_without_option_controls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            earnings = tmp / "canonical_earnings.csv"
            options = tmp / "option_events.csv"
            report = tmp / "option_report.json"
            with earnings.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["symbol", "event_date", "event_id", "event_name"])
                writer.writeheader()
                writer.writerow({"symbol": "AAA", "event_date": "2026-05-01", "event_id": "e1", "event_name": "AAA earnings"})
                writer.writerow({"symbol": "BBB", "event_date": "2026-05-02", "event_id": "e2", "event_name": "BBB earnings"})
            with options.open("w", newline="", encoding="utf-8") as handle:
                fields = ["symbol", "event_date", "coverage_status", "direction_hypothesis", "underlying_abs_fwd_1d", "underlying_fwd_1d", "underlying_path_range_1d", "underlying_mfe_1d", "underlying_mae_1d"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"symbol": "AAA", "event_date": "2026-05-01", "coverage_status": "complete", "direction_hypothesis": "bullish_activity", "underlying_abs_fwd_1d": "0.02", "underlying_fwd_1d": "0.02", "underlying_path_range_1d": "0.05", "underlying_mfe_1d": "0.03", "underlying_mae_1d": "-0.02"})
            report.write_text(json.dumps({"event_dates_requested": ["2026-05-01"]}), encoding="utf-8")
            result = run_earnings_option_split_scout(EarningsOptionSplitInputs(earnings, options, report, tmp / "out"))
            self.assertEqual(result["status"], "blocked_no_verified_earnings_without_option_abnormality_controls")
            self.assertEqual(result["earnings_with_verified_option_abnormality_count"], 1)
            self.assertEqual(result["earnings_with_verified_no_option_abnormality_count"], 0)
            with (tmp / "out" / "earnings_option_abnormality_split_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["split_status"], "earnings_with_verified_option_abnormality")
            self.assertEqual(rows[1]["split_status"], "not_option_covered")


if __name__ == "__main__":
    unittest.main()

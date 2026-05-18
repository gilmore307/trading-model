from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.option_abnormality_non_earnings_saturation import (
    NonEarningsSaturationInputs,
    run_non_earnings_saturation_study,
)


class OptionAbnormalityNonEarningsSaturationTests(unittest.TestCase):
    def _write(self, path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_reports_saturation_when_non_earnings_windows_all_have_events(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            option_events = tmp / "option_events.csv"
            earnings = tmp / "earnings.csv"
            self._write(
                option_events,
                ["symbol", "event_date", "direction_hypothesis", "underlying_abs_fwd_1d", "underlying_fwd_1d", "underlying_path_range_1d", "underlying_mfe_1d", "underlying_mae_1d"],
                [
                    {"symbol": "AAA", "event_date": "2026-05-01", "direction_hypothesis": "bullish_activity", "underlying_abs_fwd_1d": "0.01", "underlying_fwd_1d": "0.01", "underlying_path_range_1d": "0.03", "underlying_mfe_1d": "0.02", "underlying_mae_1d": "-0.01"},
                    {"symbol": "AAA", "event_date": "2026-05-01", "direction_hypothesis": "bearish_activity", "underlying_abs_fwd_1d": "0.01", "underlying_fwd_1d": "0.01", "underlying_path_range_1d": "0.03", "underlying_mfe_1d": "0.02", "underlying_mae_1d": "-0.01"},
                ],
            )
            self._write(earnings, ["symbol", "event_date"], [])
            report = run_non_earnings_saturation_study(NonEarningsSaturationInputs(option_events, earnings, tmp / "out"))
            self.assertEqual(report["status"], "current_option_event_standard_saturated_no_clean_non_earnings_controls")
            self.assertEqual(report["non_earnings_symbol_date_count"], 1)
            self.assertEqual(report["non_earnings_verified_no_abnormality_count"], 0)


if __name__ == "__main__":
    unittest.main()

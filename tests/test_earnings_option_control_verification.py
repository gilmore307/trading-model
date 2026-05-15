from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_option_control_verification import (
    EarningsOptionControlVerificationInputs,
    summarize_earnings_option_control_verification,
)


class EarningsOptionControlVerificationTests(unittest.TestCase):
    def _write(self, path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_no_abnormality_status_when_all_sampled_contracts_are_clean(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            earnings = tmp / "earnings.csv"
            existing = tmp / "existing.csv"
            probes = tmp / "probes.csv"
            bars = tmp / "bars.csv"
            self._write(earnings, ["symbol", "event_date", "event_id", "event_name"], [{"symbol": "AAA", "event_date": "2026-05-01", "event_id": "e1", "event_name": "AAA earnings"}])
            self._write(existing, ["symbol", "event_date"], [])
            self._write(
                probes,
                ["symbol", "event_date", "status", "option_event_count"],
                [
                    {"symbol": "AAA", "event_date": "2026-05-01", "status": "succeeded", "option_event_count": 0},
                    {"symbol": "AAA", "event_date": "2026-05-01", "status": "succeeded", "option_event_count": 0},
                ],
            )
            self._write(
                bars,
                ["symbol", "timestamp", "bar_close", "bar_high", "bar_low"],
                [
                    {"symbol": "AAA", "timestamp": "2026-05-01T00:00:00-04:00", "bar_close": 100, "bar_high": 101, "bar_low": 99},
                    {"symbol": "AAA", "timestamp": "2026-05-04T00:00:00-04:00", "bar_close": 104, "bar_high": 105, "bar_low": 98},
                ],
            )
            report = summarize_earnings_option_control_verification(EarningsOptionControlVerificationInputs(earnings, existing, probes, (bars,), tmp / "out"))
            self.assertEqual(report["status"], "sampled_split_available_not_promotion_evidence")
            self.assertEqual(report["status_counts"]["verified_no_sampled_option_abnormality"], 1)

    def test_partial_contract_coverage_keeps_abnormality_but_not_clean_control(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            earnings = tmp / "earnings.csv"
            existing = tmp / "existing.csv"
            probes = tmp / "probes.csv"
            bars = tmp / "bars.csv"
            self._write(earnings, ["symbol", "event_date", "event_id", "event_name"], [{"symbol": "BBB", "event_date": "2026-05-01", "event_id": "e2", "event_name": "BBB earnings"}])
            self._write(existing, ["symbol", "event_date"], [])
            self._write(
                probes,
                ["symbol", "event_date", "status", "option_event_count"],
                [
                    {"symbol": "BBB", "event_date": "2026-05-01", "status": "succeeded", "option_event_count": 3},
                    {"symbol": "BBB", "event_date": "2026-05-01", "status": "failed", "option_event_count": 0},
                ],
            )
            self._write(bars, ["symbol", "timestamp", "bar_close", "bar_high", "bar_low"], [])
            report = summarize_earnings_option_control_verification(EarningsOptionControlVerificationInputs(earnings, existing, probes, (bars,), tmp / "out"))
            self.assertEqual(report["status"], "blocked_no_verified_no_option_abnormality_controls_in_sampled_contracts")
            self.assertEqual(report["status_counts"]["partial_contract_coverage_with_verified_option_abnormality"], 1)


if __name__ == "__main__":
    unittest.main()

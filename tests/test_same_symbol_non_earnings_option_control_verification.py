from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.same_symbol_non_earnings_option_control_verification import (
    SameSymbolNonEarningsOptionControlInputs,
    summarize_same_symbol_non_earnings_option_controls,
)


class SameSymbolNonEarningsOptionControlVerificationTests(unittest.TestCase):
    def _write_csv(self, path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def _write_receipt(self, root: Path, symbol: str, event_date: str, contract: str, status: str, event_count: int) -> None:
        path = root / symbol / event_date / contract / "completion_receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "runs": [
                        {
                            "status": status,
                            "row_counts": {"option_activity_event": event_count},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_clean_non_earnings_control_split_is_recorded_but_not_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            earnings = tmp / "earnings.csv"
            option_events = tmp / "option_events.csv"
            matrix_root = tmp / "matrix"
            self._write_csv(
                earnings,
                ["symbol", "event_date", "event_id", "event_name"],
                [{"symbol": "AAA", "event_date": "2026-05-10", "event_id": "e1", "event_name": "AAA earnings"}],
            )
            self._write_receipt(matrix_root, "AAA", "2026-05-01", "call_100_events", "succeeded", 0)
            self._write_receipt(matrix_root, "AAA", "2026-05-10", "call_100_events", "succeeded", 2)
            self._write_csv(
                option_events,
                ["symbol", "event_date", "coverage_status", "underlying_abs_fwd_5d", "underlying_path_range_5d"],
                [{"symbol": "AAA", "event_date": "2026-05-10", "coverage_status": "complete", "underlying_abs_fwd_5d": 0.05, "underlying_path_range_5d": 0.08}],
            )
            report = summarize_same_symbol_non_earnings_option_controls(
                SameSymbolNonEarningsOptionControlInputs(earnings, matrix_root, option_events, tmp / "out", control_exclusion_days=3)
            )
            self.assertEqual(report["status"], "sampled_same_symbol_control_split_available_not_promotion_evidence")
            self.assertEqual(report["same_symbol_non_earnings_verified_no_abnormality_count"], 1)
            with (tmp / "out" / "same_symbol_non_earnings_option_control_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertIn("same_symbol_non_earnings_control_candidate", {row["window_role"] for row in rows})

    def test_non_earnings_abnormality_without_clean_controls_blocks_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            earnings = tmp / "earnings.csv"
            option_events = tmp / "option_events.csv"
            matrix_root = tmp / "matrix"
            self._write_csv(
                earnings,
                ["symbol", "event_date", "event_id", "event_name"],
                [{"symbol": "BBB", "event_date": "2026-05-10", "event_id": "e2", "event_name": "BBB earnings"}],
            )
            self._write_receipt(matrix_root, "BBB", "2026-05-01", "call_100_events", "succeeded", 4)
            self._write_receipt(matrix_root, "BBB", "2026-05-01", "put_100_events", "failed", 0)
            self._write_csv(option_events, ["symbol", "event_date", "coverage_status"], [])
            report = summarize_same_symbol_non_earnings_option_controls(
                SameSymbolNonEarningsOptionControlInputs(earnings, matrix_root, option_events, tmp / "out", control_exclusion_days=3)
            )
            self.assertEqual(report["status"], "blocked_no_verified_same_symbol_non_earnings_no_option_abnormality_controls")
            self.assertEqual(report["same_symbol_non_earnings_verified_no_abnormality_count"], 0)
            self.assertEqual(report["same_symbol_non_earnings_verified_abnormality_count"], 1)


if __name__ == "__main__":
    unittest.main()

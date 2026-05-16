from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_expectation_baseline import (
    ExpectationBaselineInputs,
    run_expectation_baseline_readiness,
)


class EarningsGuidanceExpectationBaselineTests(unittest.TestCase):
    def _write_interpretation_rows(self, root: Path) -> Path:
        path = root / "interpretation.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "reviewed_guidance_interpretation_status"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "reviewed_guidance_interpretation_status": "partial_official_guidance_context_reviewed"})
        return path

    def test_missing_baseline_keeps_signed_claims_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            interpretation = self._write_interpretation_rows(root)
            report = run_expectation_baseline_readiness(ExpectationBaselineInputs(interpretation, root / "out"))
            self.assertEqual(report["missing_baseline_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_expectation_baseline_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["expectation_baseline_status"], "missing_point_in_time_expectation_baseline")
            self.assertIn("eps_consensus", row["missing_required_baseline_types"])

    def test_complete_predated_baseline_set_is_ready_but_not_signed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            interpretation = self._write_interpretation_rows(root)
            manifest = root / "baselines.json"
            manifest.write_text(json.dumps({"baseline_artifacts": [
                {"event_id": "e1", "symbol": "XYZ", "baseline_type": "eps_consensus", "source_name": "test", "source_ref": "eps", "captured_at": "2025-10-29T12:00:00", "as_of_time": "2025-10-29T12:00:00"},
                {"event_id": "e1", "symbol": "XYZ", "baseline_type": "revenue_consensus", "source_name": "test", "source_ref": "rev", "captured_at": "2025-10-29T12:00:00", "as_of_time": "2025-10-29T12:00:00"},
                {"event_id": "e1", "symbol": "XYZ", "baseline_type": "prior_company_guidance", "source_name": "test", "source_ref": "guide", "captured_at": "2025-10-29T12:00:00", "as_of_time": "2025-10-29T12:00:00"},
            ]}) + "\n", encoding="utf-8")
            report = run_expectation_baseline_readiness(ExpectationBaselineInputs(interpretation, root / "out", manifest))
            self.assertEqual(report["accepted_baseline_set_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_expectation_baseline_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["expectation_baseline_status"], "accepted_point_in_time_expectation_baseline_set")
            self.assertEqual(row["signed_direction_readiness"], "baseline_ready_but_signed_claim_still_requires_result_guidance_comparison")

    def test_same_day_date_only_baseline_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            interpretation = self._write_interpretation_rows(root)
            manifest = root / "baselines.json"
            manifest.write_text(json.dumps({"baseline_artifacts": [
                {"event_id": "e1", "symbol": "XYZ", "baseline_type": "eps_consensus", "source_name": "test", "source_ref": "eps", "captured_at": "2025-10-30", "as_of_time": "2025-10-30"},
            ]}) + "\n", encoding="utf-8")
            run_expectation_baseline_readiness(ExpectationBaselineInputs(interpretation, root / "out", manifest))
            with (root / "out" / "earnings_guidance_expectation_baseline_artifacts.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["baseline_acceptance_status"], "rejected_not_point_in_time_before_event")


if __name__ == "__main__":
    unittest.main()

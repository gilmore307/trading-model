from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_readiness_scout import (
    GuidanceReadinessInputs,
    run_guidance_readiness_scout,
)


class EarningsGuidanceReadinessScoutTests(unittest.TestCase):
    def test_missing_guidance_and_expectation_blocks_signed_direction(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            events = tmp / "interpreted.csv"
            fields = [
                "symbol",
                "event_id",
                "event_date",
                "event_name",
                "lifecycle_class",
                "official_result_artifact_status",
                "result_interpretation_status",
                "result_metric_count",
                "result_direction_score",
                "guidance_status",
                "event_abs_fwd_1d",
                "event_directional_fwd_1d",
                "event_path_range_1d",
                "event_mfe_1d",
                "event_mae_1d",
            ]
            with events.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "symbol": "XYZ",
                        "event_id": "e1",
                        "event_date": "2025-10-30",
                        "event_name": "XYZ earnings",
                        "lifecycle_class": "scheduled_known_outcome_later",
                        "official_result_artifact_status": "present",
                        "result_interpretation_status": "partial_official_result_interpretation",
                        "result_metric_count": "2",
                        "result_direction_score": "1.0",
                        "guidance_status": "missing_official_guidance_interpretation",
                        "event_abs_fwd_1d": "0.02",
                        "event_directional_fwd_1d": "0.01",
                        "event_path_range_1d": "0.04",
                        "event_mfe_1d": "0.03",
                        "event_mae_1d": "-0.01",
                    }
                )
            report = run_guidance_readiness_scout(GuidanceReadinessInputs(events, tmp / "out"))
            self.assertEqual(report["status"], "blocked_missing_guidance_and_expectation_baselines")
            self.assertEqual(report["official_result_artifact_count"], 1)
            self.assertEqual(report["official_guidance_interpretation_count"], 0)
            self.assertEqual(report["expectation_baseline_count"], 0)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (tmp / "out" / "earnings_guidance_readiness_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["event_risk_context_readiness"], "partial_result_context_only")
            self.assertEqual(rows[0]["signed_direction_readiness"], "blocked_missing_guidance_and_expectation_baseline")


if __name__ == "__main__":
    unittest.main()

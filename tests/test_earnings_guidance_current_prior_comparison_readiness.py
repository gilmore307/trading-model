from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_current_prior_comparison_readiness import (
    CurrentPriorComparisonReadinessInputs,
    run_current_prior_comparison_readiness,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class EarningsGuidanceCurrentPriorComparisonReadinessTests(unittest.TestCase):
    def test_blocks_when_prior_context_exists_but_current_context_is_only_partial(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            _write_csv(
                root / "prior_events.csv",
                [
                    {
                        "symbol": "AMD",
                        "event_id": "cal_1",
                        "event_date": "2025-11-04",
                        "prior_guidance_baseline_status": "accepted_prior_company_guidance_context_baseline",
                        "accepted_prior_guidance_span_count": 5,
                    }
                ],
            )
            _write_csv(root / "prior_spans.csv", [{"event_id": "cal_1", "span_index": 1}])
            _write_csv(root / "current_rows.csv", [{"symbol": "AMD", "event_id": "cal_1", "event_date": "2025-11-04"}])
            _write_csv(
                root / "current_spans.csv",
                [
                    {
                        "event_id": "cal_1",
                        "reviewed_guidance_span_status": "partial_official_guidance_context_reviewed",
                        "evidence_text": "expected to enable future AI infrastructure deployment",
                    }
                ],
            )
            _write_csv(
                root / "result_events.csv",
                [{"symbol": "AMD", "event_id": "cal_1", "official_result_artifact_status": "present", "result_metric_count": 3}],
            )
            report = run_current_prior_comparison_readiness(
                CurrentPriorComparisonReadinessInputs(
                    prior_event_rows_path=root / "prior_events.csv",
                    prior_span_rows_path=root / "prior_spans.csv",
                    current_review_rows_path=root / "current_rows.csv",
                    current_review_spans_path=root / "current_spans.csv",
                    result_event_rows_path=root / "result_events.csv",
                    output_dir=root / "out",
                )
            )
            self.assertEqual(report["status"], "blocked_missing_current_comparable_guidance_context")
            self.assertEqual(report["accepted_prior_guidance_baseline_event_count"], 1)
            self.assertEqual(report["current_comparable_guidance_event_count"], 0)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_current_prior_comparison_readiness_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["guidance_comparison_readiness"], "blocked_missing_current_comparable_guidance_context")
            self.assertEqual(row["signed_direction_readiness"], "blocked_missing_current_guidance_comparison")
            self.assertEqual(row["event_risk_governor_readiness"], "direction_neutral_context_only")

    def test_even_comparable_context_remains_unsigned_without_pit_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            _write_csv(
                root / "prior_events.csv",
                [
                    {
                        "symbol": "COIN",
                        "event_id": "cal_2",
                        "event_date": "2025-10-30",
                        "prior_guidance_baseline_status": "accepted_prior_company_guidance_context_baseline",
                        "accepted_prior_guidance_span_count": 4,
                    }
                ],
            )
            _write_csv(root / "prior_spans.csv", [{"event_id": "cal_2", "span_index": 1}])
            _write_csv(root / "current_rows.csv", [{"symbol": "COIN", "event_id": "cal_2", "event_date": "2025-10-30"}])
            _write_csv(
                root / "current_spans.csv",
                [
                    {
                        "event_id": "cal_2",
                        "reviewed_guidance_span_status": "accepted_current_comparable_guidance_context",
                        "evidence_text": "Q4 outlook revenue range is provided by the company.",
                    }
                ],
            )
            _write_csv(
                root / "result_events.csv",
                [{"symbol": "COIN", "event_id": "cal_2", "official_result_artifact_status": "present", "result_metric_count": 2}],
            )
            report = run_current_prior_comparison_readiness(
                CurrentPriorComparisonReadinessInputs(
                    prior_event_rows_path=root / "prior_events.csv",
                    prior_span_rows_path=root / "prior_spans.csv",
                    current_review_rows_path=root / "current_rows.csv",
                    current_review_spans_path=root / "current_spans.csv",
                    result_event_rows_path=root / "result_events.csv",
                    output_dir=root / "out",
                )
            )
            self.assertEqual(report["status"], "partial_current_prior_comparison_context_only")
            self.assertEqual(report["current_comparable_guidance_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_current_prior_comparison_readiness_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(
                row["guidance_comparison_readiness"],
                "current_prior_guidance_context_comparable_pending_pit_expectation_baselines",
            )
            self.assertEqual(row["signed_direction_readiness"], "blocked_pending_pit_expectation_baselines_and_review")


if __name__ == "__main__":
    unittest.main()

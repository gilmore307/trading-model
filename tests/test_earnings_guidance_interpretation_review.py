from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_interpretation_review import (
    GuidanceInterpretationReviewInputs,
    run_guidance_interpretation_review,
)


class EarningsGuidanceInterpretationReviewTests(unittest.TestCase):
    def _write_inputs(self, root: Path, evidence_text: str, candidate_class: str = "candidate_guidance_or_outlook_text") -> tuple[Path, Path]:
        rows = root / "rows.csv"
        with rows.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "event_name", "result_accession_number", "result_primary_document"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_name": "XYZ earnings", "result_accession_number": "a1", "result_primary_document": "x.htm"})
        spans = root / "spans.csv"
        with spans.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "result_accession_number", "result_primary_document", "span_index", "candidate_class", "matched_terms", "evidence_text"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "result_accession_number": "a1", "result_primary_document": "x.htm", "span_index": "1", "candidate_class": candidate_class, "matched_terms": "expect", "evidence_text": evidence_text})
        return rows, spans

    def test_partial_context_remains_blocked_without_expectation_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            rows, spans = self._write_inputs(root, "We expect costs to total approximately $600 million through 2026.")
            report = run_guidance_interpretation_review(GuidanceInterpretationReviewInputs(rows, spans, root / "out"))
            self.assertEqual(report["partial_guidance_context_event_count"], 1)
            self.assertEqual(report["expectation_baseline_count"], 0)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_interpretation_review_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["reviewed_guidance_interpretation_status"], "partial_official_guidance_context_reviewed")
            self.assertEqual(row["accepted_guidance_raise_cut_status"], "missing_not_established")

    def test_boilerplate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            rows, spans = self._write_inputs(root, "Forward-looking statements are based on current expectations and actual results could differ.", "boilerplate_or_safe_harbor")
            report = run_guidance_interpretation_review(GuidanceInterpretationReviewInputs(rows, spans, root / "out"))
            self.assertEqual(report["partial_guidance_context_event_count"], 0)
            with (root / "out" / "earnings_guidance_interpretation_review_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["reviewed_guidance_interpretation_status"], "reviewed_no_accepted_guidance_context")


if __name__ == "__main__":
    unittest.main()

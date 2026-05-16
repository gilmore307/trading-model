from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_prior_guidance_extraction import (
    PriorGuidanceExtractionInputs,
    run_prior_guidance_extraction,
)


class PriorGuidanceExtractionTests(unittest.TestCase):
    def _write_coverage(self, root: Path, text: str) -> Path:
        doc = root / "doc.txt"
        doc.write_text(text, encoding="utf-8")
        path = root / "coverage.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "prior_accession_number", "prior_filing_date", "prior_form", "prior_primary_document", "prior_official_document_coverage_status", "prior_document_text_path"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "prior_accession_number": "a1", "prior_filing_date": "2025-07-30", "prior_form": "8-K", "prior_primary_document": "x.htm", "prior_official_document_coverage_status": "prior_official_document_text_present_uninterpreted", "prior_document_text_path": str(doc)})
        return path

    def test_accepts_explicit_prior_guidance_context_without_signed_claims(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            coverage = self._write_coverage(root, "Other Guidance: The company expects working capital outflow of $0.5 to $1.5 billion in third quarter 2025.")
            report = run_prior_guidance_extraction(PriorGuidanceExtractionInputs(coverage, root / "out"))
            self.assertEqual(report["accepted_prior_guidance_baseline_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_prior_guidance_baseline_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_guidance_baseline_status"], "accepted_prior_company_guidance_context_baseline")

    def test_rejects_forward_looking_boilerplate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            coverage = self._write_coverage(root, "Forward-looking statements include expectations, estimates, and projections. Actual results could differ.")
            report = run_prior_guidance_extraction(PriorGuidanceExtractionInputs(coverage, root / "out"))
            self.assertEqual(report["accepted_prior_guidance_baseline_event_count"], 0)
            with (root / "out" / "earnings_guidance_prior_guidance_baseline_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_guidance_baseline_status"], "reviewed_no_prior_guidance_context_found")


if __name__ == "__main__":
    unittest.main()

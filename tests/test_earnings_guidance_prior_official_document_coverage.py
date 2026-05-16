from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_prior_official_document_coverage import (
    PriorOfficialDocumentCoverageInputs,
    run_prior_official_document_coverage,
)


class PriorOfficialDocumentCoverageTests(unittest.TestCase):
    def test_detects_present_document_text(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            source = root / "source.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "prior_accession_number", "prior_filing_date", "prior_form", "prior_primary_document"])
                writer.writeheader()
                writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "prior_accession_number": "0000000001-25-000001", "prior_filing_date": "2025-07-30", "prior_form": "8-K", "prior_primary_document": "xyz.htm"})
            saved = root / "docs" / "XYZ" / "runs" / "run1" / "saved"
            saved.mkdir(parents=True)
            text = saved / "sec_filing_document_text.txt"
            text.write_text("official text", encoding="utf-8")
            metadata = saved / "sec_filing_document.csv"
            with metadata.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["accession_number", "document_text_path", "text_length"])
                writer.writeheader()
                writer.writerow({"accession_number": "0000000001-25-000001", "document_text_path": str(text), "text_length": "13"})
            report = run_prior_official_document_coverage(PriorOfficialDocumentCoverageInputs(source, root / "docs", root / "out"))
            self.assertEqual(report["prior_official_document_text_present_event_count"], 1)
            with (root / "out" / "earnings_guidance_prior_official_document_coverage_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_official_document_coverage_status"], "prior_official_document_text_present_uninterpreted")


if __name__ == "__main__":
    unittest.main()

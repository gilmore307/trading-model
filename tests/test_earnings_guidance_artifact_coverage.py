from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_artifact_coverage import (
    GuidanceArtifactCoverageInputs,
    run_guidance_artifact_coverage_scout,
)


class EarningsGuidanceArtifactCoverageScoutTests(unittest.TestCase):
    def test_missing_local_document_blocks_guidance_interpretation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            events = tmp / "events.csv"
            with events.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "event_name", "lifecycle_class", "result_accession_number"])
                writer.writeheader()
                writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_name": "XYZ earnings", "lifecycle_class": "scheduled_known_outcome_later", "result_accession_number": "0000000000-25-000001"})
            filings = tmp / "filings.csv"
            with filings.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "accession_number", "primary_document", "form", "filing_date"])
                writer.writeheader()
                writer.writerow({"event_id": "e1", "accession_number": "0000000000-25-000001", "primary_document": "xyz-20251030.htm", "form": "8-K", "filing_date": "2025-10-30"})

            report = run_guidance_artifact_coverage_scout(GuidanceArtifactCoverageInputs(events, filings, tmp / "out"))

            self.assertEqual(report["status"], "blocked_missing_local_official_guidance_artifacts")
            self.assertEqual(report["result_filing_reference_count"], 1)
            self.assertEqual(report["local_official_document_text_artifact_count"], 0)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (tmp / "out" / "earnings_guidance_artifact_coverage_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["official_guidance_artifact_status"], "missing_local_official_document_text_artifact")

    def test_local_document_without_accepted_interpretation_still_blocks_signed_direction(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            text = tmp / "sec_filing_document_text.txt"
            text.write_text("Official outlook text", encoding="utf-8")
            events = tmp / "events.csv"
            with events.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "event_name", "lifecycle_class"])
                writer.writeheader()
                writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_name": "XYZ earnings", "lifecycle_class": "scheduled_known_outcome_later"})
            filings = tmp / "filings.csv"
            with filings.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "accession_number", "primary_document"])
                writer.writeheader()
                writer.writerow({"event_id": "e1", "accession_number": "0000000000-25-000001", "primary_document": "xyz-20251030.htm"})
            metadata = tmp / "sec_filing_document.csv"
            with metadata.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["accession_number", "document_name", "text_length", "text_sha256", "document_text_path"])
                writer.writeheader()
                writer.writerow({"accession_number": "0000000000-25-000001", "document_name": "xyz-20251030.htm", "text_length": "21", "text_sha256": "abc", "document_text_path": str(text)})

            report = run_guidance_artifact_coverage_scout(
                GuidanceArtifactCoverageInputs(events, filings, tmp / "out", sec_filing_document_metadata_paths=(metadata,))
            )

            self.assertEqual(report["status"], "blocked_missing_accepted_guidance_interpretation_or_expectation_baseline")
            self.assertEqual(report["local_official_document_text_artifact_count"], 1)
            self.assertEqual(report["accepted_guidance_interpretation_count"], 0)
            with (tmp / "out" / "earnings_guidance_artifact_coverage_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["official_guidance_artifact_status"], "official_document_text_present_uninterpreted")
            self.assertEqual(rows[0]["signed_direction_readiness"], "blocked_missing_guidance_interpretation_or_expectation_baseline")

    def test_relative_text_path_is_resolved_from_metadata_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            saved = repo / "storage" / "task" / "runs" / "run" / "saved"
            saved.mkdir(parents=True)
            text = saved / "sec_filing_document_text.txt"
            text.write_text("Official filing text", encoding="utf-8")
            events = repo / "events.csv"
            with events.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "event_name", "lifecycle_class"])
                writer.writeheader()
                writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_name": "XYZ earnings", "lifecycle_class": "scheduled_known_outcome_later"})
            filings = repo / "filings.csv"
            with filings.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["event_id", "accession_number", "primary_document"])
                writer.writeheader()
                writer.writerow({"event_id": "e1", "accession_number": "0000000000-25-000001", "primary_document": "xyz-20251030.htm"})
            metadata = saved / "sec_filing_document.csv"
            with metadata.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["accession_number", "document_name", "text_length", "text_sha256", "document_text_path"])
                writer.writeheader()
                writer.writerow({
                    "accession_number": "0000000000-25-000001",
                    "document_name": "xyz-20251030.htm",
                    "text_length": "20",
                    "text_sha256": "abc",
                    "document_text_path": "storage/task/runs/run/saved/sec_filing_document_text.txt",
                })

            report = run_guidance_artifact_coverage_scout(
                GuidanceArtifactCoverageInputs(events, filings, repo / "out", sec_filing_document_metadata_paths=(metadata,))
            )

            self.assertEqual(report["local_official_document_text_artifact_count"], 1)
            with (repo / "out" / "earnings_guidance_artifact_coverage_rows.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["local_document_text_path_status"], "present")
            self.assertEqual(rows[0]["official_guidance_artifact_status"], "official_document_text_present_uninterpreted")


if __name__ == "__main__":
    unittest.main()

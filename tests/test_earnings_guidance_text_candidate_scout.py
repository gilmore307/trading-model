from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_text_candidate_scout import (
    GuidanceTextCandidateInputs,
    run_guidance_text_candidate_scout,
)


class EarningsGuidanceTextCandidateScoutTests(unittest.TestCase):
    def _write_base_inputs(self, root: Path, text: str) -> tuple[Path, Path, Path]:
        saved = root / "storage" / "doc" / "runs" / "run" / "saved"
        saved.mkdir(parents=True)
        text_path = saved / "sec_filing_document_text.txt"
        text_path.write_text(text, encoding="utf-8")
        metadata = saved / "sec_filing_document.csv"
        with metadata.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["accession_number", "document_name", "document_text_path", "text_length", "text_sha256"])
            writer.writeheader()
            writer.writerow({"accession_number": "0000000000-25-000001", "document_name": "xyz.htm", "document_text_path": "storage/doc/runs/run/saved/sec_filing_document_text.txt", "text_length": str(len(text)), "text_sha256": "abc"})
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"document_metadata": [{"metadata_path": str(metadata)}]}) + "\n", encoding="utf-8")
        events = root / "events.csv"
        with events.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date", "event_name"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_name": "XYZ earnings"})
        filings = root / "filings.csv"
        with filings.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["event_id", "accession_number", "primary_document"])
            writer.writeheader()
            writer.writerow({"event_id": "e1", "accession_number": "0000000000-25-000001", "primary_document": "xyz.htm"})
        return events, filings, manifest

    def test_candidate_guidance_text_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events, filings, manifest = self._write_base_inputs(root, "<p>The company expects full year revenue to increase and projects margin improvement.</p>")
            report = run_guidance_text_candidate_scout(GuidanceTextCandidateInputs(events, filings, manifest, root / "out"))
            self.assertEqual(report["candidate_guidance_text_event_count"], 1)
            self.assertEqual(report["accepted_guidance_interpretation_count"], 0)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_text_candidate_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["guidance_candidate_status"], "candidate_guidance_text_present_review_required")
            self.assertEqual(row["signed_direction_readiness"], "blocked_missing_reviewed_guidance_interpretation_or_expectation_baseline")

    def test_boilerplate_forward_looking_text_is_separated(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events, filings, manifest = self._write_base_inputs(root, "Forward-looking statements include expectations and forecasts; actual results could differ due to risk factors.")
            report = run_guidance_text_candidate_scout(GuidanceTextCandidateInputs(events, filings, manifest, root / "out"))
            self.assertEqual(report["candidate_guidance_text_event_count"], 0)
            self.assertEqual(report["boilerplate_only_event_count"], 1)
            with (root / "out" / "earnings_guidance_text_candidate_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["guidance_candidate_status"], "boilerplate_or_safe_harbor_only_review_required")


if __name__ == "__main__":
    unittest.main()

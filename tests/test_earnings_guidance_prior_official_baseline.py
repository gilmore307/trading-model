from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.earnings_guidance_prior_official_baseline import (
    PriorOfficialBaselineInputs,
    run_prior_official_baseline_audit,
)


class PriorOfficialBaselineAuditTests(unittest.TestCase):
    def _write_events(self, root: Path) -> Path:
        path = root / "events.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "event_id", "event_date"])
            writer.writeheader()
            writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30"})
        return path

    def _write_submission(self, root: Path, form: str = "8-K", filing_date: str = "2025-07-30") -> Path:
        saved = root / "XYZ" / "runs" / "run1" / "saved"
        saved.mkdir(parents=True)
        path = saved / "sec_submission.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["cik", "company_name", "accession_number", "filing_date", "report_date", "form", "primary_document", "primary_doc_description"])
            writer.writeheader()
            writer.writerow({"cik": "0000000001", "company_name": "XYZ", "accession_number": "0000000001-25-000001", "filing_date": filing_date, "report_date": filing_date, "form": form, "primary_document": "xyz.htm", "primary_doc_description": form})
        return root

    def test_selects_pre_event_official_filing_candidate_and_task_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events = self._write_events(root)
            submissions = self._write_submission(root / "submissions")
            report = run_prior_official_baseline_audit(PriorOfficialBaselineInputs(events, submissions, root / "out"))
            self.assertEqual(report["candidate_source_event_count"], 1)
            with (root / "out" / "earnings_guidance_prior_official_baseline_source_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_official_guidance_source_status"], "candidate_prior_official_guidance_source_selected")
            payload = json.loads((root / "out" / "prior_official_guidance_document_task_keys.jsonl").read_text().strip())
            self.assertEqual(payload["params"]["data_kind"], "sec_filing_document")
            self.assertEqual(payload["params"]["current_event_id"], "e1")

    def test_rejects_post_event_filing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            events = self._write_events(root)
            submissions = self._write_submission(root / "submissions", filing_date="2025-11-01")
            report = run_prior_official_baseline_audit(PriorOfficialBaselineInputs(events, submissions, root / "out"))
            self.assertEqual(report["candidate_source_event_count"], 0)
            with (root / "out" / "earnings_guidance_prior_official_baseline_source_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_official_guidance_source_status"], "missing_prior_official_guidance_source_candidate")


if __name__ == "__main__":
    unittest.main()

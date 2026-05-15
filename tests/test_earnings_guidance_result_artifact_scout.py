from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_result_artifact_scout import ResultArtifactInputs, run_result_artifact_scout


class EarningsGuidanceResultArtifactScoutTests(unittest.TestCase):
    def test_sec_result_artifact_and_fact_direction_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            events = tmp / "earnings_guidance_event_windows.csv"
            submissions_dir = tmp / "sec_submission" / "XYZ" / "runs" / "r" / "saved"
            facts_dir = tmp / "sec_company_fact" / "XYZ" / "runs" / "r" / "saved"
            submissions_dir.mkdir(parents=True)
            facts_dir.mkdir(parents=True)
            submissions = submissions_dir / "sec_submission.csv"
            facts = facts_dir / "sec_company_fact.csv"
            with events.open("w", newline="", encoding="utf-8") as handle:
                fields = ["symbol", "event_id", "event_date", "event_abs_fwd_1d", "event_path_range_1d", "event_directional_fwd_1d", "event_mfe_1d", "event_mae_1d"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"symbol": "XYZ", "event_id": "e1", "event_date": "2025-10-30", "event_abs_fwd_1d": "0.02", "event_path_range_1d": "0.05", "event_directional_fwd_1d": "0.02", "event_mfe_1d": "0.03", "event_mae_1d": "-0.02"})
            with submissions.open("w", newline="", encoding="utf-8") as handle:
                fields = ["cik", "company_name", "accession_number", "filing_date", "report_date", "form", "primary_document", "primary_doc_description"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"cik": "1", "company_name": "XYZ", "accession_number": "acc-2025", "filing_date": "2025-10-31", "report_date": "2025-09-30", "form": "10-Q", "primary_document": "xyz.htm", "primary_doc_description": "10-Q"})
            with facts.open("w", newline="", encoding="utf-8") as handle:
                fields = ["cik", "entity_name", "taxonomy", "tag", "label", "description", "unit", "fy", "fp", "form", "filed", "frame", "end", "value", "accession_number"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"cik": "1", "entity_name": "XYZ", "taxonomy": "us-gaap", "tag": "RevenueFromContractWithCustomerExcludingAssessedTax", "label": "Revenue", "description": "", "unit": "USD", "fy": "2024", "fp": "Q3", "form": "10-Q", "filed": "2024-10-31", "frame": "", "end": "2024-09-30", "value": "100", "accession_number": "acc-2024"})
                writer.writerow({"cik": "1", "entity_name": "XYZ", "taxonomy": "us-gaap", "tag": "RevenueFromContractWithCustomerExcludingAssessedTax", "label": "Revenue", "description": "", "unit": "USD", "fy": "2025", "fp": "Q3", "form": "10-Q", "filed": "2025-10-31", "frame": "", "end": "2025-09-30", "value": "120", "accession_number": "acc-2025"})
            report = run_result_artifact_scout(ResultArtifactInputs(events, (submissions,), (facts,), tmp / "out"))
            self.assertEqual(report["event_count"], 1)
            self.assertEqual(report["official_result_artifact_count"], 1)
            with (tmp / "out" / "earnings_guidance_result_interpreted_events.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["result_interpretation_status"], "official_result_artifact_only")
            self.assertEqual(rows[0]["result_direction_score"], "1.0")


if __name__ == "__main__":
    unittest.main()

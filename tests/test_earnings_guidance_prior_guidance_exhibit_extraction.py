from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from models.model_04_event_overlay.earnings_guidance_prior_guidance_exhibit_extraction import (
    PriorGuidanceExhibitExtractionInputs,
    extract_prior_guidance_spans,
    run_prior_guidance_exhibit_extraction,
)


class PriorGuidanceExhibitExtractionTests(unittest.TestCase):
    def _write_task_and_document(self, root: Path, *, symbol: str, document_name: str, text: str) -> None:
        accession = "0000000000-25-000001"
        task_keys = root / "task_keys"
        task_keys.mkdir(parents=True, exist_ok=True)
        (task_keys / f"{symbol}_cal_abc_{accession.replace('-', '')}.json").write_text(
            json.dumps(
                {
                    "params": {
                        "current_event_id": "cal_abc",
                        "current_event_date": "2025-10-30",
                        "accession_number": accession,
                        "document_name": document_name,
                        "primary_document_name": "primary.htm",
                        "candidate_days_before_event": 90,
                    }
                }
            ),
            encoding="utf-8",
        )
        doc_path = root / "docs" / symbol / accession.replace("-", "") / document_name / "runs" / "run1" / "cleaned"
        doc_path.mkdir(parents=True, exist_ok=True)
        (doc_path / "sec_filing_document_text.txt").write_text(text, encoding="utf-8")

    def test_extracts_numeric_company_outlook_without_signed_claims(self) -> None:
        text = (
            "Current Outlook. For the third quarter of 2025, AMD expects revenue to be "
            "approximately $8.7 billion, plus or minus $300 million. Non-GAAP gross margin "
            "is expected to be approximately 54%."
        )
        spans = extract_prior_guidance_spans(text)
        self.assertGreaterEqual(len(spans), 1)
        self.assertEqual(spans[0]["baseline_type"], "prior_company_guidance")
        self.assertEqual(spans[0]["prior_guidance_baseline_status"], "accepted_prior_company_guidance_context_baseline")

    def test_rejects_macro_outlook_and_legal_guidance_false_positives(self) -> None:
        macro_text = (
            "The economic outlook remains uncertain. Changes in the weighted-average macroeconomic "
            "outlook were offset by loan growth. Revenue was $19.5 billion in the quarter."
        )
        legal_text = (
            "Recent SEC guidance regarding staking services is discussed in litigation updates. "
            "The company continues to engage with regulators while fighting state actions."
        )
        self.assertEqual(extract_prior_guidance_spans(macro_text), [])
        self.assertEqual(extract_prior_guidance_spans(legal_text), [])

    def test_run_accepts_shareholder_letter_exhibit_route(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            self._write_task_and_document(
                root,
                symbol="COIN",
                document_name="q225shareholderletter.htm",
                text=(
                    "Q3'25 Outlook. We expect Q3 subscription and services revenue to be within "
                    "$665-$745 million. We expect technology and development expenses to range "
                    "from $800-$850 million."
                ),
            )
            report = run_prior_guidance_exhibit_extraction(
                PriorGuidanceExhibitExtractionInputs(root / "task_keys", root / "docs", root / "out")
            )
            self.assertEqual(report["accepted_prior_guidance_baseline_event_count"], 1)
            self.assertEqual(report["signed_direction_ready_count"], 0)
            with (root / "out" / "earnings_guidance_prior_guidance_exhibit_event_rows.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["prior_guidance_baseline_status"], "accepted_prior_company_guidance_context_baseline")
            self.assertEqual(row["signed_direction_readiness"], "blocked_pending_current_guidance_comparison_and_revenue_consensus")


if __name__ == "__main__":
    unittest.main()

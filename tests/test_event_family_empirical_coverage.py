from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_family_empirical_coverage import (
    build_event_family_empirical_coverage,
    write_empirical_coverage_artifacts,
)


class EventFamilyEmpiricalCoverageTests(unittest.TestCase):
    def test_builds_coverage_for_every_family_and_preserves_safety(self) -> None:
        coverage = build_event_family_empirical_coverage(generated_at_utc="2026-05-17T02:00:00+00:00")
        payload = coverage.to_dict()

        self.assertEqual(payload["contract_type"], "event_family_empirical_coverage_v1")
        self.assertEqual(payload["summary"]["family_count"], 29)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])
        self.assertEqual(
            payload["summary"]["final_conclusion"],
            "withheld_until_family_specific_empirical_association_studies_complete",
        )

    def test_expected_family_statuses_are_conservative(self) -> None:
        coverage = build_event_family_empirical_coverage(generated_at_utc="2026-05-17T02:00:00+00:00")
        by_family = {row.family_key: row for row in coverage.family_rows}

        self.assertEqual(
            by_family["cpi_inflation_release"].coverage_status,
            "existing_empirical_studies_risk_only_needs_canonical_history",
        )
        self.assertGreater(by_family["cpi_inflation_release"].existing_empirical_artifact_count, 0)
        self.assertEqual(
            by_family["option_derivatives_abnormality"].association_readiness_status,
            "not_ready_revise_abnormality_definition_before_retest",
        )
        self.assertEqual(
            by_family["earnings_guidance_result_metrics"].association_readiness_status,
            "not_ready_build_pit_baseline_first",
        )

    def test_local_macro_candidate_detection_finds_nfp_or_cpi_rows(self) -> None:
        coverage = build_event_family_empirical_coverage(generated_at_utc="2026-05-17T02:00:00+00:00")
        by_family = {row.family_key: row for row in coverage.family_rows}

        self.assertGreater(by_family["nfp_employment_release"].local_candidate_count, 0)
        self.assertGreater(by_family["cpi_inflation_release"].local_candidate_count, 0)

    def test_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "coverage"
            coverage = build_event_family_empirical_coverage(generated_at_utc="2026-05-17T02:00:00+00:00")
            write_empirical_coverage_artifacts(coverage, output_dir)

            payload_path = output_dir / "event_family_empirical_coverage.json"
            summary_path = output_dir / "event_family_empirical_coverage_summary.json"
            actions_path = output_dir / "event_family_next_empirical_actions.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(actions_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["family_count"], 29)
            self.assertIn("cpi_inflation_release", actions_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.event_family_fixtures import build_event_family_fixture

from models.model_10_event_risk_governor.cpi_inflation_association_readiness import (
    build_cpi_inflation_association_readiness,
    write_readiness_artifacts,
)


class CpiInflationAssociationReadinessTests(unittest.TestCase):
    def _build_fixture_readiness(self, root: Path):
        fixture = build_event_family_fixture(root)
        return build_cpi_inflation_association_readiness(
            data_root=fixture.trading_data_root,
            generated_at_utc="2026-05-16T12:10:00+00:00",
        )

    def test_cpi_readiness_preserves_non_mutating_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            readiness = build_cpi_inflation_association_readiness(
                data_root=Path(raw_tmp) / "empty-trading-data",
                generated_at_utc="2026-05-16T12:10:00+00:00",
            )
        payload = readiness.to_dict()

        self.assertEqual(payload["contract_type"], "cpi_inflation_association_readiness")
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_cpi_has_event_and_control_diagnostics_but_remains_underpowered(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            readiness = self._build_fixture_readiness(Path(raw_tmp))

            self.assertIn("2016-01", readiness.calendar_months_available)
            self.assertGreater(readiness.event_count, 0)
            self.assertGreater(readiness.event_label_count, 0)
            self.assertGreater(readiness.control_label_count, 0)
            self.assertGreater(readiness.comparison_count, 0)
            self.assertEqual(readiness.association_study_status, "underpowered_cpi_scouting_only")
            self.assertIn("insufficient_local_cpi_calendar_months", readiness.blocker_codes)
            self.assertIn("needs_market_sector_target_state_controls", readiness.blocker_codes)

    def test_comparisons_include_available_event_control_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            readiness = self._build_fixture_readiness(Path(raw_tmp))
            available = [item for item in readiness.comparisons if item.comparison_status == "comparison_available"]

            self.assertTrue(available)
            self.assertTrue(all(item.control_count > 0 for item in available))
            self.assertTrue(any(item.event_minus_control_mean is not None for item in available))

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "cpi"
            readiness = self._build_fixture_readiness(Path(raw_tmp) / "fixture")
            write_readiness_artifacts(readiness, output_dir)

            summary_path = output_dir / "cpi_inflation_association_summary.json"
            full_path = output_dir / "cpi_inflation_association_readiness.json"
            comparisons_path = output_dir / "cpi_inflation_event_control_comparisons.csv"
            self.assertTrue(summary_path.exists())
            self.assertTrue(full_path.exists())
            self.assertTrue(comparisons_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["association_study_status"], "underpowered_cpi_scouting_only")
            self.assertIn("cpi_inflation_release", comparisons_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

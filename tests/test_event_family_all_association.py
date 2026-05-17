from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_family_all_association import (
    build_event_family_all_association,
    write_event_family_all_association_artifacts,
)


class EventFamilyAllAssociationTests(unittest.TestCase):
    def test_emits_all_families_and_safety_flags(self) -> None:
        association = build_event_family_all_association(generated_at_utc="2026-05-17T03:00:00+00:00")
        payload = association.to_dict()

        self.assertEqual(payload["contract_type"], "event_family_all_association_v1")
        self.assertEqual(payload["summary"]["family_count"], 29)
        self.assertEqual(payload["provider_calls"], 0)
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_key_family_results_are_explicit(self) -> None:
        association = build_event_family_all_association(generated_at_utc="2026-05-17T03:00:00+00:00")
        by_family = {row.family_key: row for row in association.family_rows}

        self.assertTrue(by_family["cpi_inflation_release"].risk_control_supported)
        self.assertFalse(by_family["cpi_inflation_release"].directional_alpha_supported)
        self.assertTrue(by_family["earnings_guidance_scheduled_shell"].risk_control_supported)
        self.assertEqual(
            by_family["option_derivatives_abnormality"].association_class,
            "current_definition_no_accepted_association",
        )
        self.assertEqual(
            by_family["nfp_employment_release"].association_class,
            "not_measured_required_precondition_missing",
        )

    def test_summary_has_no_directional_alpha_families(self) -> None:
        association = build_event_family_all_association(generated_at_utc="2026-05-17T03:00:00+00:00")
        self.assertEqual(association.summary["directional_alpha_supported_families"], [])
        self.assertEqual(
            association.summary["risk_control_supported_families"],
            ["earnings_guidance_scheduled_shell", "cpi_inflation_release"],
        )

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "assoc"
            association = build_event_family_all_association(generated_at_utc="2026-05-17T03:00:00+00:00")
            write_event_family_all_association_artifacts(association, output_dir)

            payload_path = output_dir / "event_family_all_association.json"
            summary_path = output_dir / "event_family_all_association_summary.json"
            csv_path = output_dir / "event_family_all_association.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(csv_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["family_count"], 29)
            self.assertIn("earnings_guidance_scheduled_shell", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

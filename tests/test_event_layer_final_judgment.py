from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_08_event_risk_governor.event_layer_final_judgment import (
    build_event_layer_final_judgment,
    write_event_layer_final_judgment_artifacts,
)


class EventLayerFinalJudgmentTests(unittest.TestCase):
    def test_final_posture_rejects_standalone_event_alpha(self) -> None:
        judgment = build_event_layer_final_judgment(generated_at_utc="2026-05-17T02:00:00+00:00")
        payload = judgment.to_dict()

        self.assertEqual(payload["contract_type"], "event_layer_final_judgment_v1")
        self.assertEqual(payload["final_model_posture"], "build_event_risk_governor_not_standalone_event_alpha")
        self.assertEqual(payload["final_alpha_decision"], "reject_standalone_directional_event_alpha_for_current_evidence")
        self.assertEqual(payload["final_risk_decision"], "accept_bounded_event_risk_intelligence_overlay")
        self.assertEqual(payload["summary"]["standalone_alpha_families_now"], [])
        self.assertFalse(payload["model_training_performed"])
        self.assertFalse(payload["model_activation_performed"])
        self.assertFalse(payload["broker_execution_performed"])
        self.assertFalse(payload["account_mutation_performed"])
        self.assertFalse(payload["artifact_deletion_performed"])

    def test_family_dispositions_cover_all_families(self) -> None:
        judgment = build_event_layer_final_judgment(generated_at_utc="2026-05-17T02:00:00+00:00")
        by_family = {row.family_key: row for row in judgment.family_dispositions}

        self.assertEqual(len(by_family), 29)
        self.assertEqual(
            by_family["cpi_inflation_release"].final_disposition,
            "risk_control_feature_accepted_not_alpha",
        )
        self.assertEqual(
            by_family["earnings_guidance_scheduled_shell"].final_disposition,
            "direction_neutral_event_risk_context_only",
        )
        self.assertEqual(
            by_family["option_derivatives_abnormality"].final_disposition,
            "deferred_low_signal_revise_definition",
        )
        self.assertEqual(
            by_family["equity_offering_dilution"].final_disposition,
            "source_or_parser_gap",
        )

    def test_allowed_and_prohibited_outputs_are_explicit(self) -> None:
        judgment = build_event_layer_final_judgment(generated_at_utc="2026-05-17T02:00:00+00:00")

        self.assertIn("event_risk_score_or_bucket", judgment.allowed_outputs)
        self.assertIn("human_review_required_flag", judgment.allowed_outputs)
        self.assertIn("standalone_buy_sell_hold", judgment.prohibited_outputs)
        self.assertIn("option_contract_selection", judgment.prohibited_outputs)
        self.assertIn("broker_account_mutation", judgment.prohibited_outputs)

    def test_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            output_dir = Path(raw_tmp) / "judgment"
            judgment = build_event_layer_final_judgment(generated_at_utc="2026-05-17T02:00:00+00:00")
            write_event_layer_final_judgment_artifacts(judgment, output_dir)

            payload_path = output_dir / "event_layer_final_judgment.json"
            summary_path = output_dir / "event_layer_final_judgment_summary.json"
            dispositions_path = output_dir / "event_family_final_dispositions.csv"
            self.assertTrue(payload_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(dispositions_path.exists())
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["standalone_alpha_families_now"], [])
            self.assertIn("cpi_inflation_release", dispositions_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

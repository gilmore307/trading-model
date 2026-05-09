from __future__ import annotations

import unittest

from model_governance.promotion import (
    build_model_config_ref,
    build_promotion_candidate_evidence,
    build_review_artifact_from_review,
)


class ModelPromotionEvidenceTests(unittest.TestCase):
    def test_candidate_evidence_requires_config_ref_and_eval_run(self) -> None:
        config = build_model_config_ref(
            model_id="market_regime_model",
            config_hash="factor-specs-v1",
            model_version="v1",
            config_payload={"source": "factor_specs.toml"},
        )
        candidate = build_promotion_candidate_evidence(
            model_id="market_regime_model",
            config_ref_id=config["config_ref_id"],
            eval_run_id="mdevrun_001",
            candidate_payload={"minimum_coverage": 0.8},
        )

        self.assertEqual(candidate["model_id"], "market_regime_model")
        self.assertEqual(candidate["config_ref_id"], config["config_ref_id"])
        self.assertEqual(candidate["eval_run_id"], "mdevrun_001")
        self.assertIn("candidate_ref", candidate)

    def test_promotion_evidence_refs_have_stable_ids(self) -> None:
        first = build_model_config_ref(model_id="market_regime_model", config_hash="abc")
        second = build_model_config_ref(model_id="market_regime_model", config_hash="abc")

        self.assertEqual(first["config_ref_id"], second["config_ref_id"])

    def test_review_artifact_does_not_create_active_model_pointer(self) -> None:
        artifact = build_review_artifact_from_review(
            candidate_ref="mpcandref_001",
            review={
                "can_promote": False,
                "decision_type": "defer",
                "decision_status": "deferred",
                "confidence": 0.8,
                "reasons": ["dev smoke only"],
                "blockers": ["needs real metrics"],
                "required_next_steps": ["run real eval"],
                "evidence_checks": {"has_metrics": True},
            },
        )

        self.assertEqual(artifact["candidate_ref"], "mpcandref_001")
        self.assertEqual(artifact["decision_status"], "deferred")
        self.assertTrue(artifact["manager_control_plane_required"])
        self.assertNotIn("active_model_version", artifact)
        self.assertNotIn("production_pointer", artifact)
        self.assertNotIn("activation_id", artifact)
        self.assertNotIn("rollback_id", artifact)

    def test_unsupported_decision_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_review_artifact_from_review(
                candidate_ref="mpcandref_001",
                review={
                    "can_promote": True,
                    "decision_type": "approve",
                    "decision_status": "promoted",
                    "confidence": 0.8,
                    "reasons": ["x"],
                    "blockers": [],
                    "required_next_steps": [],
                    "evidence_checks": {"has_metrics": True},
                },
            )


if __name__ == "__main__":
    unittest.main()

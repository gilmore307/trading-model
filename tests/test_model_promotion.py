from __future__ import annotations

import unittest

from model_governance.promotion import (
    build_config_version_row,
    build_promotion_candidate_row,
    build_promotion_decision_row,
    build_promotion_rollback_row,
)


class ModelPromotionTests(unittest.TestCase):
    def test_candidate_requires_config_version_and_eval_run(self) -> None:
        config = build_config_version_row(
            model_id="market_regime_model",
            config_hash="factor-specs-v1",
            model_version="v1",
            config_payload={"source": "factor_specs.toml"},
        )
        candidate = build_promotion_candidate_row(
            model_id="market_regime_model",
            config_version_id=config["config_version_id"],
            eval_run_id="mdevrun_001",
            candidate_payload={"minimum_coverage": 0.8},
        )

        self.assertEqual(candidate["model_id"], "market_regime_model")
        self.assertEqual(candidate["config_version_id"], config["config_version_id"])
        self.assertEqual(candidate["eval_run_id"], "mdevrun_001")
        self.assertEqual(candidate["candidate_status"], "proposed")

    def test_promotion_rows_have_stable_ids(self) -> None:
        first = build_config_version_row(model_id="market_regime_model", config_hash="abc")
        second = build_config_version_row(model_id="market_regime_model", config_hash="abc")

        self.assertEqual(first["config_version_id"], second["config_version_id"])

    def test_decision_does_not_create_active_model_pointer(self) -> None:
        decision = build_promotion_decision_row(
            promotion_candidate_id="mpcand_001",
            decision_type="approve",
            decision_status="accepted",
            decided_by="openclaw",
            decision_payload={"thresholds_checked": True},
        )

        self.assertEqual(decision["promotion_candidate_id"], "mpcand_001")
        self.assertNotIn("active_model_version", decision)
        self.assertNotIn("production_pointer", decision)

    def test_unsupported_decision_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_promotion_decision_row(
                promotion_candidate_id="mpcand_001",
                decision_type="approve",
                decision_status="promoted",
            )

    def test_rollback_row_tracks_from_and_optional_to_config_versions(self) -> None:
        rollback = build_promotion_rollback_row(
            model_id="market_regime_model",
            from_config_version_id="mcfg_current",
            to_config_version_id="mcfg_previous",
            promotion_decision_id="mpdec_001",
            requested_by="openclaw",
        )

        self.assertEqual(rollback["rollback_status"], "requested")
        self.assertEqual(rollback["from_config_version_id"], "mcfg_current")
        self.assertEqual(rollback["to_config_version_id"], "mcfg_previous")
        self.assertEqual(rollback["promotion_decision_id"], "mpdec_001")


if __name__ == "__main__":
    unittest.main()

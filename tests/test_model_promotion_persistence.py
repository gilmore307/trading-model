from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from model_governance.persistence import render_promotion_persistence_sql
from model_governance.promotion import (
    build_config_version_row,
    build_promotion_candidate_row,
    build_promotion_decision_row,
)


class ModelPromotionPersistenceTests(unittest.TestCase):
    def _rows(self) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        config = build_config_version_row(
            model_id="model_01_market_regime",
            model_version="model_01_market_regime",
            config_hash="factor-specs-v1",
        )
        candidate = build_promotion_candidate_row(
            model_id="model_01_market_regime",
            config_version_id=str(config["config_version_id"]),
            eval_run_id="mdevrun_001",
        )
        decision = build_promotion_decision_row(
            promotion_candidate_id=str(candidate["promotion_candidate_id"]),
            decision_type="approve",
            decision_status="accepted",
            decided_by="reviewer",
            decision_payload={"thresholds_checked": True},
        )
        return config, candidate, decision

    def test_render_sql_persists_evidence_decision_and_activation(self) -> None:
        config, candidate, decision = self._rows()
        artifacts = {
            "model_dataset_request": [
                {
                    "request_id": "mdreq_001",
                    "model_id": "model_01_market_regime",
                    "purpose": "promotion_eval",
                    "required_data_start_time": "2026-01-01T00:00:00-05:00",
                    "required_data_end_time": "2026-01-02T00:00:00-05:00",
                    "required_source_key": "SOURCE_01_MARKET_REGIME",
                    "required_feature_key": "FEATURE_01_MARKET_REGIME",
                    "request_status": "completed",
                    "request_payload_json": {"fixture": False},
                }
            ]
        }

        sql = render_promotion_persistence_sql(
            evaluation_artifacts=artifacts,
            config_version_row=config,
            promotion_candidate_row=candidate,
            promotion_decision_row=decision,
            activate_approved_config=True,
        )

        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_promotion_decision"', sql)
        self.assertIn('INSERT INTO "trading_model"."model_dataset_request"', sql)
        self.assertIn('INSERT INTO "trading_model"."model_config_version"', sql)
        self.assertIn('INSERT INTO "trading_model"."model_promotion_candidate"', sql)
        self.assertIn('INSERT INTO "trading_model"."model_promotion_decision"', sql)
        self.assertIn('INSERT INTO "trading_model"."model_promotion_activation"', sql)
        self.assertIn('SET "config_status" = \'retired\'', sql)
        self.assertIn('SET "config_status" = \'active\'', sql)

    def test_deferred_decision_does_not_render_activation(self) -> None:
        config, candidate, _decision = self._rows()
        decision = build_promotion_decision_row(
            promotion_candidate_id=str(candidate["promotion_candidate_id"]),
            decision_type="defer",
            decision_status="deferred",
        )

        sql = render_promotion_persistence_sql(
            evaluation_artifacts=None,
            config_version_row=config,
            promotion_candidate_row=candidate,
            promotion_decision_row=decision,
            activate_approved_config=True,
        )

        self.assertIn("Promotion decision persisted", sql)
        self.assertNotIn('INSERT INTO "trading_model"."model_promotion_activation"', sql)
        self.assertNotIn('SET "config_status" = \'active\'', sql)

    def test_review_script_can_preview_persistence_sql_without_database(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        summary = {
            "eval_run_id": "mdevrun_001",
            "database_write_policy": "development_tables_written_then_cleaned",
            "cleanup_policy": "cleanup_after_run",
            "tables": {"model_promotion_metric": 3},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary.json"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_01_market_regime/review_market_regime_promotion.py",
                    "--evaluation-summary-json",
                    str(summary_path),
                    "--local-fallback-review",
                    "--print-write-sql",
                ],
                cwd=repo_root,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=True,
            )

        self.assertIn('INSERT INTO "trading_model"."model_promotion_decision"', result.stdout)
        self.assertIn("SQL PREVIEW ONLY", result.stdout)
        self.assertIn("no active config was changed", result.stdout)


if __name__ == "__main__":
    unittest.main()

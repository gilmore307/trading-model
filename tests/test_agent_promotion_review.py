from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.models.model_01_market_regime.review_market_regime_promotion as review_script
from model_governance.agent_review import (
    build_decision_row_from_review,
    build_market_regime_promotion_prompt,
    extract_json_object,
    validate_promotion_review,
)
from model_governance.promotion import build_config_version_row, build_promotion_candidate_row


class AgentPromotionReviewTests(unittest.TestCase):
    def _summary(self) -> dict[str, object]:
        return {
            "eval_run_id": "mdevrun_001",
            "database_write_policy": "development_tables_written_then_cleaned",
            "cleanup_policy": "cleanup_after_run",
            "tables": {"model_eval_metric": 211},
        }

    def test_prompt_requires_strict_json_and_blocks_fixture_only_approval(self) -> None:
        config = build_config_version_row(model_id="model_01_market_regime", config_hash="abc")
        candidate = build_promotion_candidate_row(
            model_id="model_01_market_regime",
            config_version_id=config["config_version_id"],
            eval_run_id="mdevrun_001",
        )

        prompt = build_market_regime_promotion_prompt(
            evaluation_summary=self._summary(),
            config_version_row=config,
            promotion_candidate_row=candidate,
        )

        self.assertIn("Return ONLY one JSON object", prompt)
        self.assertIn("Do not approve if evidence is fixture-only", prompt)
        self.assertIn("mdevrun_001", prompt)

    def test_review_validation_rejects_inconsistent_approval(self) -> None:
        with self.assertRaises(ValueError):
            validate_promotion_review(
                {
                    "can_promote": False,
                    "decision_type": "approve",
                    "decision_status": "accepted",
                    "confidence": 0.5,
                    "reasons": ["x"],
                    "blockers": ["y"],
                    "required_next_steps": ["z"],
                    "evidence_checks": {"has_metrics": True},
                }
            )

    def test_valid_review_builds_decision_row_without_active_pointer(self) -> None:
        review = validate_promotion_review(
            {
                "can_promote": False,
                "decision_type": "defer",
                "decision_status": "deferred",
                "confidence": 0.8,
                "reasons": ["dev smoke only"],
                "blockers": ["needs real metrics"],
                "required_next_steps": ["run real eval"],
                "evidence_checks": {"has_metrics": True},
            }
        )
        decision = build_decision_row_from_review(promotion_candidate_id="mpcand_001", review=review)

        self.assertEqual(decision["decision_type"], "defer")
        self.assertEqual(decision["decision_status"], "deferred")
        self.assertNotIn("active_model_version", decision)
        self.assertNotIn("production_pointer", decision)

    def test_extract_json_object_tolerates_wrapped_output(self) -> None:
        parsed = extract_json_object('prefix {"can_promote": false, "decision_type": "defer"} suffix')

        self.assertEqual(parsed["decision_type"], "defer")

    def test_extract_agent_text_reads_openclaw_payloads(self) -> None:
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": json.dumps(
                                {
                                    "can_promote": False,
                                    "decision_type": "defer",
                                    "decision_status": "deferred",
                                    "confidence": 0.7,
                                    "reasons": ["missing thresholds"],
                                    "blockers": ["thresholds"],
                                    "required_next_steps": ["define thresholds"],
                                    "evidence_checks": {"has_metrics": True},
                                }
                            )
                        }
                    ]
                },
            }
        )

        review = validate_promotion_review(extract_json_object(review_script._extract_agent_text(stdout)))

        self.assertEqual(review["decision_type"], "defer")

    def test_review_script_dry_run_does_not_invoke_agent(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary.json"
            summary_path.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_01_market_regime/review_market_regime_promotion.py",
                    "--evaluation-summary-json",
                    str(summary_path),
                    "--dry-run",
                ],
                cwd=repo_root,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=True,
            )

        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertIn("agent_prompt", result.stdout)
        self.assertIn("promotion_candidate", result.stdout)

    def test_local_fallback_treats_no_database_write_summary_as_not_real_promotion_evidence(self) -> None:
        review = review_script._fallback_review(
            {
                "eval_run_id": "mdevrun_001",
                "write_policy": "no_database_write",
                "tables": {"model_eval_metric": 211},
            }
        )

        self.assertFalse(review["can_promote"])
        self.assertFalse(review["evidence_checks"]["has_real_non_fixture_data"])

    def test_review_script_local_fallback_defers_dev_smoke_promotion(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary.json"
            summary_path.write_text(json.dumps(self._summary()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_01_market_regime/review_market_regime_promotion.py",
                    "--evaluation-summary-json",
                    str(summary_path),
                    "--local-fallback-review",
                ],
                cwd=repo_root,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=True,
            )

        payload_text = result.stdout.split("\nREVIEW ONLY:", 1)[0]
        payload = json.loads(payload_text)
        self.assertFalse(payload["agent_review"]["can_promote"])
        self.assertEqual(payload["promotion_decision"]["decision_type"], "defer")


if __name__ == "__main__":
    unittest.main()

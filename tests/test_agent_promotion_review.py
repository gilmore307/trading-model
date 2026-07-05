from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import scripts.models.review_current_model_promotion_acceptance as current_model_review_script
from model_governance.agent_review import (
    build_review_artifact_from_review,
    extract_json_object,
    validate_promotion_review,
)


class AgentPromotionReviewTests(unittest.TestCase):
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

    def test_valid_review_builds_artifact_without_active_pointer(self) -> None:
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
        artifact = build_review_artifact_from_review(candidate_ref="mpcandref_001", review=review)

        self.assertEqual(artifact["decision_type"], "defer")
        self.assertEqual(artifact["decision_status"], "deferred")
        self.assertNotIn("active_model_version", artifact)
        self.assertNotIn("production_pointer", artifact)

    def test_extract_json_object_tolerates_wrapped_output(self) -> None:
        parsed = extract_json_object('prefix {"can_promote": false, "decision_type": "defer"} suffix')

        self.assertEqual(parsed["decision_type"], "defer")

    def test_current_model_agent_text_reads_top_level_openclaw_payloads(self) -> None:
        stdout = json.dumps(
            {
                "payloads": [
                    {
                        "text": json.dumps(
                            {
                                "can_promote": False,
                                "decision_type": "defer",
                                "decision_status": "deferred",
                                "confidence": 1.0,
                                "reasons": ["missing production eval substrate"],
                                "blockers": ["no production eval run"],
                                "required_next_steps": ["create production eval run"],
                                "evidence_checks": {"production_evaluation_substrate_present": False},
                            }
                        )
                    }
                ]
            }
        )

        review = validate_promotion_review(extract_json_object(current_model_review_script._extract_agent_text(stdout)))

        self.assertEqual(review["decision_status"], "deferred")
        self.assertFalse(review["evidence_checks"]["production_evaluation_substrate_present"])

    def test_current_model_acceptance_uses_current_model_map(self) -> None:
        by_model = {item["model_number"]: item for item in current_model_review_script.MODEL_ACCEPTANCES}

        self.assertEqual(sorted(by_model), list(range(3, 6)))
        self.assertEqual(by_model[3]["model_id"], "event_state_model")
        self.assertEqual(by_model[4]["model_name"], "UnifiedDecisionModel")
        self.assertEqual(by_model[5]["model_id"], "option_expression_model")

    def test_current_model_dry_run_builds_blocked_artifacts_without_agent(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                "scripts/models/review_current_model_promotion_acceptance.py",
                "--model-number",
                "3",
                "--dry-run",
            ],
            cwd=repo_root,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        receipt = payload["receipts"][0]
        self.assertEqual(receipt["summary"]["run_status"], "blocked")
        self.assertIn("Return ONLY one JSON object", receipt["agent_prompt"])
        self.assertFalse(receipt["summary"]["promotion_evidence_ready"])


if __name__ == "__main__":
    unittest.main()

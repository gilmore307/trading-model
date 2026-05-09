from __future__ import annotations

import unittest

from model_governance.promotion import (
    LAYER_PROMOTION_READINESS_MATRIX,
    REQUIRED_PROMOTION_EVIDENCE_FIELDS,
    validate_promotion_evidence_package,
)


class PromotionReadinessTests(unittest.TestCase):
    def test_readiness_matrix_covers_layers_one_through_eight(self) -> None:
        layers = [row["layer"] for row in LAYER_PROMOTION_READINESS_MATRIX]

        self.assertEqual(layers, list(range(1, 9)))
        self.assertTrue(all(row["design_status"] == "design_closed" for row in LAYER_PROMOTION_READINESS_MATRIX))
        statuses = {row["production_promotion_status"] for row in LAYER_PROMOTION_READINESS_MATRIX}
        self.assertNotIn("production_approved", statuses)
        self.assertIn("deferred_after_real_evaluation", statuses)
        self.assertIn("deferred_no_production_eval_substrate", statuses)
        self.assertTrue(all("mpdec_" not in row["blocking_gap"] for row in LAYER_PROMOTION_READINESS_MATRIX))
        self.assertTrue(all("persisted decision" not in row["blocking_gap"] for row in LAYER_PROMOTION_READINESS_MATRIX))

    def test_missing_evidence_forces_defer(self) -> None:
        result = validate_promotion_evidence_package(
            {
                "dataset_snapshot_ref": "snapshot_001",
                "eval_run_ref": "eval_run_001",
                "requested_decision_status": "approved",
            }
        )

        self.assertFalse(result["approval_allowed"])
        self.assertTrue(result["defer_required"])
        self.assertEqual(result["review_action"], "defer_promotion")
        self.assertIn("dataset_split_ref", result["missing_evidence_fields"])
        self.assertFalse(result["approval_request_is_valid"])

    def test_complete_evidence_with_passing_gates_may_be_reviewed_for_approval(self) -> None:
        evidence = {field: f"{field}_001" for field in REQUIRED_PROMOTION_EVIDENCE_FIELDS}
        evidence["eval_label_refs"] = ["label_5min", "label_390min"]
        evidence["promotion_metric_refs"] = ["metric_baseline_lift", "metric_stability"]
        evidence["gate_results"] = {
            "baseline_improvement": True,
            "split_stability": True,
            "leakage_check": True,
            "calibration_check": True,
        }
        evidence["requested_decision_status"] = "approved"

        result = validate_promotion_evidence_package(evidence)

        self.assertTrue(result["approval_allowed"])
        self.assertFalse(result["defer_required"])
        self.assertEqual(result["review_action"], "review_may_consider_approval")
        self.assertEqual(result["missing_evidence_fields"], [])
        self.assertEqual(result["failed_gate_names"], [])
        self.assertTrue(result["approval_request_is_valid"])

    def test_failed_gate_forces_defer_even_when_fields_exist(self) -> None:
        evidence = {field: f"{field}_001" for field in REQUIRED_PROMOTION_EVIDENCE_FIELDS}
        evidence["gate_results"] = {"baseline_improvement": True, "split_stability": False}

        result = validate_promotion_evidence_package(evidence)

        self.assertFalse(result["approval_allowed"])
        self.assertEqual(result["failed_gate_names"], ["split_stability"])


if __name__ == "__main__":
    unittest.main()

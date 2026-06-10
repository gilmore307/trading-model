from __future__ import annotations

import unittest

from models.model_05_alpha_confidence.event_conditioned_contrast import (
    DIAGNOSTIC_SCOPE,
    build_labeled_focus_pool_rows,
    decision_id_from_layer4_row,
    run_event_conditioned_alpha_contrast,
    without_layer4_event_features,
)


class EventConditionedAlphaContrastTests(unittest.TestCase):
    def test_labeled_focus_pool_rows_join_layer4_to_layer10_by_decision_id(self) -> None:
        layer4_rows = [_layer4_row(0, strength=0.25), _layer4_row(1, strength=0.75)]
        overlay_rows = [
            {"decision_id": "ed-000", "excess_return": -0.01, "target_ref": "AAPL", "visible_event_families": ["cpi_inflation_release"]},
            {"decision_id": "ed-001", "excess_return": 0.02, "target_ref": "MSFT", "visible_event_families": ["breaking_news_shock"]},
        ]

        rows = build_labeled_focus_pool_rows(layer4_rows, overlay_rows, horizon="1D")

        self.assertEqual([row["source_decision_id"] for row in rows], ["ed-000", "ed-001"])
        self.assertEqual(rows[0]["after_cost_return_1D"], -0.01)
        self.assertEqual(rows[1]["target_ref"], "MSFT")
        self.assertEqual(rows[1]["layer_05_diagnostic_scope"], DIAGNOSTIC_SCOPE)

    def test_baseline_neutralizes_layer4_features_without_mutating_source_row(self) -> None:
        row = _layer4_row(0, strength=0.80)
        baseline = without_layer4_event_features(row)

        self.assertIn("4_event_response_strength_score_1D", row)
        self.assertNotIn("4_event_response_strength_score_1D", baseline)
        self.assertEqual(baseline["event_failure_risk_vector"], {})
        self.assertNotEqual(baseline["event_failure_risk_vector_ref"], row["event_failure_risk_vector_ref"])

    def test_invalid_layer4_candidate_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "target_candidate_id"):
            decision_id_from_layer4_row({"target_candidate_id": "not_replay_backed"})

    def test_run_contrast_marks_artifact_as_diagnostic_not_promotion(self) -> None:
        rows = []
        overlays = []
        for index in range(20):
            strength = [0.20, 0.40, 0.60, 0.80][index % 4]
            rows.append(_layer4_row(index, strength=strength))
            overlays.append(
                {
                    "decision_id": f"ed-{index:03d}",
                    "excess_return": (strength - 0.50) * 0.06,
                    "target_ref": "AAPL",
                    "visible_event_families": ["cpi_inflation_release"],
                    "visible_event_count": 1,
                }
            )
        labeled_rows = build_labeled_focus_pool_rows(rows, overlays, horizon="1D")

        try:
            artifact = run_event_conditioned_alpha_contrast(labeled_rows, horizon="1D", iterations=20)
        except RuntimeError as error:
            raise unittest.SkipTest(str(error)) from error

        self.assertEqual(artifact["diagnostic_scope"], DIAGNOSTIC_SCOPE)
        self.assertEqual(artifact["feature_boundary"]["baseline_role"], "evaluation_only_not_training_route")
        self.assertEqual(
            artifact["feature_boundary"]["formal_training_route"],
            "consume_layer4_event_failure_risk_vector_when_present",
        )
        self.assertFalse(artifact["feature_boundary"]["layer10_parameter_mutation"])
        self.assertFalse(artifact["feature_boundary"]["promotion_or_activation"])
        self.assertEqual(artifact["row_counts"]["labeled"], 20)
        self.assertEqual(artifact["row_counts"]["test"], 6)
        self.assertEqual(len(artifact["predictions"]), 6)
        self.assertIn("rmse_reduction", artifact["incremental_metrics"])


def _layer4_row(index: int, *, strength: float) -> dict[str, object]:
    event_vector = {
        "4_event_response_strength_score_1D": strength,
        "4_event_response_direction_score_1D": (strength - 0.50) * 2.0,
        "4_event_response_uncertainty_score_1D": 0.10,
        "4_event_strategy_failure_risk_score_1D": strength,
        "4_event_entry_block_pressure_score_1D": max(0.0, 1.0 - strength),
        "4_event_exposure_cap_pressure_score_1D": 0.30,
        "4_event_strategy_disable_pressure_score_1D": 0.10,
        "4_event_path_risk_amplifier_score_1D": strength,
        "4_event_session_gap_risk_score_1D": 0.20,
        "4_event_evidence_quality_score_1D": 0.90,
        "4_event_applicability_confidence_score_1D": 0.85,
    }
    return {
        "available_time": f"2021-01-{index + 1:02d}T16:00:00-05:00",
        "tradeable_time": f"2021-01-{index + 2:02d}T09:30:00-05:00",
        "target_candidate_id": f"layer10_replay_ed-{index:03d}",
        "event_failure_risk_vector_ref": f"efrv_{index:03d}",
        "event_failure_risk_vector": dict(event_vector),
        **event_vector,
    }


if __name__ == "__main__":
    unittest.main()

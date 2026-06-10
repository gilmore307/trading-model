from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.model_06_residual_event_governance import generate_rows
from models.model_06_residual_event_governance.evaluation import (
    assert_no_label_leakage,
    build_residual_event_governance_labels,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_OUTPUT_FIELDS = {
    "underlying_action_plan",
    "underlying_action_vector",
    "underlying_action_plan_ref",
    "base_underlying_action_plan_ref",
    "event_context_vector",
    "event_context_vector_ref",
}


class ResidualEventGovernanceModelTests(unittest.TestCase):
    def test_generates_current_intervention_from_m04_and_optional_m05_context(self) -> None:
        output = generate_rows([_base_row()])[0]
        intervention = output["event_risk_intervention"]
        diagnostics = output["residual_event_governance_diagnostics"]

        self.assertEqual(output["model_id"], "residual_event_governance_model")
        self.assertEqual(output["model_step"], "M06")
        self.assertEqual(output["unified_decision_vector_ref"], "udv_fixture")
        self.assertEqual(output["option_expression_plan_ref"], "oep_fixture")
        self.assertIn("event_risk_intervention_ref", output)
        self.assertGreater(output["6_event_presence_score_1D"], 0.0)
        self.assertLess(output["6_event_symbol_impact_score_1D"], 0.0)
        self.assertIn(output["6_resolved_intervention_action"], {"warn", "cap_new_exposure", "block_new_entry", "reduce_or_flatten_review"})
        self.assertEqual(intervention["governed_thesis_refs"]["unified_decision_vector_ref"], "udv_fixture")
        self.assertTrue(diagnostics["no_broker_or_account_mutation"])
        self.assertEqual(diagnostics["migration_source"], "model_10_event_risk_governor_scoring")
        assert_no_label_leakage(output)
        self.assert_no_retired_outputs(output)

    def test_optional_option_expression_ref_can_be_absent(self) -> None:
        row = _base_row()
        row.pop("option_expression_plan_ref")
        row.pop("option_expression_plan")

        output = generate_rows([row])[0]

        self.assertNotIn("option_expression_plan_ref", output)
        self.assertNotIn("option_expression_plan_ref", output["event_risk_intervention"]["governed_thesis_refs"])
        self.assertEqual(output["unified_decision_vector_ref"], "udv_fixture")
        self.assert_no_retired_outputs(output)

    def test_no_visible_event_stays_neutral(self) -> None:
        output = generate_rows([_base_row(event_observations=[])])[0]

        self.assertEqual(output["6_event_presence_score_1W"], 0.0)
        self.assertEqual(output["6_resolved_intervention_action"], "no_intervention")
        self.assertIn("no_visible_point_in_time_event", output["6_resolved_reason_codes"])

    def test_labels_are_offline_and_join_by_intervention_ref(self) -> None:
        output = generate_rows([_base_row()])[0]
        labels = build_residual_event_governance_labels(
            [output],
            [
                {
                    "event_risk_intervention_ref": output["event_risk_intervention_ref"],
                    "realized_residual_event_loss_1W": -0.04,
                    "realized_intervention_utility_1W": 0.05,
                    "missed_event_failure_label_1W": False,
                }
            ],
        )

        self.assertEqual(len(labels), 1)
        self.assertAlmostEqual(labels[0]["realized_intervention_utility_1W"], 0.05)
        self.assertNotIn("realized_intervention_utility_1W", output)

    def test_current_script_fixture_emits_residual_event_governance_rows(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/model_06_residual_event_governance/generate_model_06_residual_event_governance.py"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 1)
        self.assertIn("event_risk_intervention", rows[0])
        self.assertIn("6_event_presence_score_1D", rows[0])
        self.assertNotIn("event_context_vector", rows[0])

    def test_current_script_column_type_uses_model_06_prefix(self) -> None:
        script = _load_generator_script()

        self.assertEqual(script._column_type("6_event_gap_risk_score_1W"), "DOUBLE PRECISION")
        self.assertEqual(script._column_type("6_resolved_intervention_action"), "TEXT")
        self.assertEqual(script._column_type("10_event_gap_risk_score_1W"), "TEXT")

    def test_current_generate_evaluate_review_scripts_support_help(self) -> None:
        scripts = [
            "scripts/models/model_06_residual_event_governance/generate_model_06_residual_event_governance.py",
            "scripts/models/model_06_residual_event_governance/evaluate_model_06_residual_event_governance.py",
            "scripts/models/model_06_residual_event_governance/review_residual_event_governance_promotion.py",
        ]

        for script in scripts:
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, script, "--help"],
                    cwd=REPO_ROOT,
                    env={"PYTHONPATH": "src"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_current_evaluate_and_review_scripts_defer_fixture_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "summary.json"
            review_path = Path(tmp) / "review.json"
            eval_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_06_residual_event_governance/evaluate_model_06_residual_event_governance.py",
                    "--output-json",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(eval_result.returncode, 0, eval_result.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["summary"]["model_surface"], "model_06_residual_event_governance")
            self.assertEqual(summary["summary"]["promotion_gate_state"], "deferred")

            review_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/models/model_06_residual_event_governance/review_residual_event_governance_promotion.py",
                    "--evaluation-summary-json",
                    str(summary_path),
                    "--output-json",
                    str(review_path),
                ],
                cwd=REPO_ROOT,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(review_result.returncode, 0, review_result.stderr)
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["decision_status"], "deferred")
            self.assertFalse(review["activation_allowed"])

    def assert_no_retired_outputs(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key), RETIRED_OUTPUT_FIELDS)
                self.assert_no_retired_outputs(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_retired_outputs(nested)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "available_time": "2026-05-07T10:30:00-04:00",
        "tradeable_time": "2026-05-07T10:31:00-04:00",
        "target_candidate_id": "anon_target_001",
        "symbol_for_join_only": "AAPL",
        "sector_type": "technology",
        "background_context_state_ref": "bcs_fixture",
        "target_context_state_ref": "tcs_fixture",
        "event_state_vector_ref": "esv_fixture",
        "unified_decision_vector_ref": "udv_fixture",
        "option_expression_plan_ref": "oep_fixture",
        "target_context_state": {
            "2_target_direction_score_1W": 0.5,
            "2_target_direction_score_1h": 0.4,
        },
        "direct_underlying_intent": {
            "underlying_action_type": "open_long",
            "action_side": "long",
            "dominant_horizon": "1W",
        },
        "option_expression_plan": {
            "selected_expression_type": "long_call",
            "option_surface_status": "optionable_chain_available",
        },
        "event_observations": [
            {
                "event_id": "evt_fixture_canonical",
                "canonical_event_id": "evt_fixture_canonical",
                "dedup_status": "new_information",
                "source_priority": 1,
                "event_time": "2026-05-07T10:10:00-04:00",
                "available_time": "2026-05-07T10:12:00-04:00",
                "event_category_type": "sec_filing",
                "scope_type": "symbol",
                "symbol": "AAPL",
                "sector_type": "technology",
                "event_intensity_score": 0.9,
                "direction_bias_score": -0.7,
                "target_relevance_score": 1.0,
                "scope_confidence_score": 0.9,
            }
        ],
    }
    row.update(overrides)
    return row


def _load_generator_script():
    script = REPO_ROOT / "scripts/models/model_06_residual_event_governance/generate_model_06_residual_event_governance.py"
    spec = importlib.util.spec_from_file_location(script.stem, script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

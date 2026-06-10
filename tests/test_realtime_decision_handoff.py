from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.realtime_decision_handoff import (
    build_realtime_decision_route_plan,
    validate_execution_model_decision_input_snapshot,
    validate_realtime_decision_route_plan,
)


def _decision_input_snapshot() -> dict[str, object]:
    components = [
        ("background_context_component", "background_context_model", "background_context_state"),
        ("target_state_component", "target_state_model", "target_context_state"),
        ("event_state_component", "event_state_model", "event_state_vector"),
        ("unified_decision_component", "unified_decision_model", "unified_decision_vector"),
        ("option_expression_component", "option_expression_model", "option_expression_plan"),
        ("residual_event_governance_component", "residual_event_governance_model", "event_risk_intervention"),
    ]
    return {
        "contract_type": "execution_model_decision_input_snapshot",
        "decision_input_snapshot_id": "rtdecision_unit",
        "decision_time": "2026-05-11T13:30:00+00:00",
        "instrument_ref": "AAPL",
        "dataset_role": "shadow_monitoring",
        "historical_dataset_snapshot_ref": "trading-model://snapshots/historical/unit",
        "frozen_model_config_ref": "trading-model://configs/frozen/unit",
        "realtime_feature_snapshot_ref": "realtime-feature-snapshot://rtfeat_unit",
        "component_input_refs": [
            {
                "contract_type": "execution_model_decision_component_input",
                "decision_input_snapshot_id": "rtdecision_unit",
                "model_component": component,
                "model_id": model_id,
                "expected_model_output": output,
                "feature_ref": f"realtime-feature://rtfeat_unit/{component}",
                "upstream_context_refs": [f"placeholder://upstream/{component}"],
                "frozen_model_config_ref": "trading-model://configs/frozen/unit",
                "historical_dataset_snapshot_ref": "trading-model://snapshots/historical/unit",
                "realtime_feature_snapshot_ref": "realtime-feature-snapshot://rtfeat_unit",
                "decision_handoff_status": "ready_for_historical_model_decision_input",
            }
            for component, model_id, output in components
        ],
    }


class RealtimeDecisionHandoffTests(unittest.TestCase):
    def test_validate_execution_input_requires_all_required_components(self) -> None:
        snapshot = _decision_input_snapshot()
        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"], result["row_errors"])
        self.assertEqual(result["execution_unit"], "component")
        self.assertEqual(result["missing_components"], [])
        self.assertEqual(result["provider_calls_performed"], 0)
        self.assertFalse(result["model_activation_performed"])

    def test_option_expression_component_is_optional_for_direct_underlying_route(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["instrument_ref"] = "BTC-USD"
        snapshot["asset_expression_route"] = "direct_underlying_only"
        snapshot["component_input_refs"] = [
            row for row in snapshot["component_input_refs"] if row["model_component"] != "option_expression_component"
        ]

        result = validate_execution_model_decision_input_snapshot(snapshot)
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": snapshot})
        validation = validate_realtime_decision_route_plan(plan)

        self.assertTrue(result["valid"], result["row_errors"])
        self.assertEqual(result["missing_components"], [])
        self.assertEqual(result["missing_optional_components"], ["option_expression_component"])
        self.assertEqual(len(plan["component_routes"]), 5)
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_component_route")
        self.assertTrue(validation["valid"], validation["row_errors"])
        self.assertEqual(validation["missing_optional_components"], ["option_expression_component"])

    def test_option_expression_component_accepts_trading_guidance_output(self) -> None:
        snapshot = _decision_input_snapshot()
        for row in snapshot["component_input_refs"]:
            if row["model_component"] == "option_expression_component":
                row["expected_model_output"] = "trading_guidance_record"

        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"], result["row_errors"])

    def test_build_route_plan_maps_all_components_to_current_generators(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})

        self.assertEqual(plan["contract_type"], "model_realtime_decision_route_plan")
        self.assertEqual(plan["execution_unit"], "component")
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_component_route")
        self.assertEqual(len(plan["component_routes"]), 6)
        self.assertEqual(plan["provider_calls_performed"], 0)
        self.assertFalse(plan["model_activation_performed"])
        self.assertFalse(plan["broker_order_construction_performed"])
        decision = plan["component_routes"][3]
        self.assertEqual(decision["model_component"], "unified_decision_component")
        self.assertEqual(decision["model_step"], "M04")
        self.assertEqual(decision["expected_model_output"], "unified_decision_vector")
        self.assertIn("generate_model_04_unified_decision.py", decision["generator_entrypoint_ref"])
        option = plan["component_routes"][4]
        self.assertEqual(option["model_component"], "option_expression_component")
        self.assertEqual(option["invocation_policy"], "conditional_after_unified_decision_or_option_applicability")
        self.assertIn("generate_model_05_option_expression.py", option["generator_entrypoint_ref"])
        residual = plan["component_routes"][-1]
        self.assertEqual(residual["model_component"], "residual_event_governance_component")
        self.assertEqual(residual["expected_model_output"], "event_risk_intervention")
        self.assertIn("generate_model_06_residual_event_governance.py", residual["generator_entrypoint_ref"])
        validation = validate_realtime_decision_route_plan(plan)
        self.assertTrue(validation["valid"], validation["row_errors"])

    def test_forbidden_model_activation_blocks_input_validation(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["requested_actions"] = ["model_activation"]

        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertFalse(result["valid"])
        self.assertIn("model_activation", result["forbidden_actions_present"])

    def test_live_dataset_role_is_not_valid_shadow_input(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["dataset_role"] = "live_production"

        result = validate_execution_model_decision_input_snapshot(snapshot)
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": snapshot})

        self.assertFalse(result["valid"])
        self.assertFalse(result["dataset_role_valid"])
        self.assertEqual(plan["readiness_status"], "blocked_realtime_decision_input_validation")

    def test_route_plan_validation_rechecks_model_identity_and_output(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})
        plan["component_routes"][-1]["model_id"] = "stale_event_risk_governor"
        plan["component_routes"][3]["expected_model_output"] = "underlying_action_plan"

        validation = validate_realtime_decision_route_plan(plan)

        self.assertFalse(validation["valid"])
        self.assertIn(
            "component_routes[5].model_id mismatch for residual_event_governance_component",
            validation["row_errors"],
        )
        self.assertIn(
            "component_routes[3].expected_model_output mismatch for unified_decision_component",
            validation["row_errors"],
        )

    def test_cli_plans_and_validates_route_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "decision_input.json"
            plan_path = Path(temp_dir) / "route_plan.json"
            input_path.write_text(json.dumps(_decision_input_snapshot()), encoding="utf-8")

            plan_result = subprocess.run(
                [sys.executable, "scripts/models/plan_realtime_decision_handoff.py", str(input_path)],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )
            plan = json.loads(plan_result.stdout)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_component_route")

            validate_result = subprocess.run(
                [sys.executable, "scripts/models/validate_realtime_decision_handoff.py", str(plan_path)],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )
            validation = json.loads(validate_result.stdout)
            self.assertTrue(validation["valid"])
            self.assertFalse(validation["model_activation_performed"])


if __name__ == "__main__":
    unittest.main()

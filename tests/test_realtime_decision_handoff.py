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
        ("component_01_intake", "C01", "Intake", ("model_01_background_context", "model_02_target_state"), ()),
        (
            "component_02_entry",
            "C02",
            "Entry",
            ("model_03_event_state", "model_04_unified_decision"),
            ("model_06_residual_event_governance",),
        ),
        (
            "component_03_lifecycle",
            "C03",
            "Lifecycle",
            ("model_03_event_state", "model_04_unified_decision"),
            ("model_06_residual_event_governance",),
        ),
        ("component_04_option_review", "C04", "Option Review", (), ("model_05_option_expression", "model_06_residual_event_governance")),
        ("component_05_order_intent", "C05", "Order Intent", (), ()),
        ("component_06_execution_gate", "C06", "Execution Gate", (), ()),
        ("component_07_failure_review", "C07", "Failure Review", (), ("model_06_residual_event_governance",)),
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
                "component_id": component_id,
                "component_step": component_step,
                "component_name": component_name,
                "required_model_surfaces": list(required_surfaces),
                "optional_model_surfaces": list(optional_surfaces),
                "feature_ref": f"realtime-feature://rtfeat_unit/{component_id}",
                "upstream_context_refs": [f"placeholder://upstream/{component_id}"],
                "frozen_model_config_ref": "trading-model://configs/frozen/unit",
                "historical_dataset_snapshot_ref": "trading-model://snapshots/historical/unit",
                "realtime_feature_snapshot_ref": "realtime-feature-snapshot://rtfeat_unit",
                "decision_handoff_status": "ready_for_historical_model_decision_input",
            }
            for component_id, component_step, component_name, required_surfaces, optional_surfaces in components
        ],
    }


class RealtimeDecisionHandoffTests(unittest.TestCase):
    def test_validate_execution_input_requires_all_required_runtime_components(self) -> None:
        snapshot = _decision_input_snapshot()
        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"], result["row_errors"])
        self.assertEqual(result["execution_unit"], "runtime_component")
        self.assertEqual(result["missing_components"], [])
        self.assertEqual(result["provider_calls_performed"], 0)
        self.assertFalse(result["model_activation_performed"])

    def test_option_review_and_failure_review_are_optional_component_routes(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["instrument_ref"] = "BTC-USD"
        snapshot["asset_expression_route"] = "direct_underlying_only"
        snapshot["component_input_refs"] = [
            row
            for row in snapshot["component_input_refs"]
            if row["component_id"] not in {"component_04_option_review", "component_07_failure_review"}
        ]

        result = validate_execution_model_decision_input_snapshot(snapshot)
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": snapshot})
        validation = validate_realtime_decision_route_plan(plan)

        self.assertTrue(result["valid"], result["row_errors"])
        self.assertEqual(result["missing_components"], [])
        self.assertEqual(result["missing_optional_components"], ["component_04_option_review", "component_07_failure_review"])
        self.assertEqual(len(plan["component_routes"]), 5)
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_runtime_component_route")
        self.assertTrue(validation["valid"], validation["row_errors"])
        self.assertEqual(validation["missing_optional_components"], ["component_04_option_review", "component_07_failure_review"])

    def test_build_route_plan_maps_all_components_to_current_model_surfaces(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})

        self.assertEqual(plan["contract_type"], "model_realtime_decision_route_plan")
        self.assertEqual(plan["execution_unit"], "runtime_component")
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_runtime_component_route")
        self.assertEqual(len(plan["component_routes"]), 7)
        self.assertEqual(plan["provider_calls_performed"], 0)
        self.assertFalse(plan["model_activation_performed"])
        self.assertFalse(plan["broker_order_construction_performed"])
        intake = plan["component_routes"][0]
        self.assertEqual(intake["component_id"], "component_01_intake")
        self.assertEqual(intake["component_step"], "C01")
        self.assertEqual(intake["required_model_surfaces"], ["model_01_background_context", "model_02_target_state"])
        entry = plan["component_routes"][1]
        self.assertEqual(entry["component_id"], "component_02_entry")
        self.assertEqual(entry["required_model_surfaces"], ["model_03_event_state", "model_04_unified_decision"])
        self.assertEqual(entry["optional_model_surfaces"], ["model_06_residual_event_governance"])
        option = plan["component_routes"][3]
        self.assertEqual(option["component_id"], "component_04_option_review")
        self.assertEqual(option["optional_model_surfaces"], ["model_05_option_expression", "model_06_residual_event_governance"])
        order_intent = plan["component_routes"][4]
        self.assertEqual(order_intent["component_id"], "component_05_order_intent")
        self.assertEqual(order_intent["required_model_surfaces"], [])
        self.assertEqual(order_intent["model_entrypoint_refs"], [])
        residual = plan["component_routes"][-1]
        self.assertEqual(residual["component_id"], "component_07_failure_review")
        self.assertEqual(residual["optional_model_surfaces"], ["model_06_residual_event_governance"])
        validation = validate_realtime_decision_route_plan(plan)
        self.assertTrue(validation["valid"], validation["row_errors"])

    def test_component_surface_mismatch_blocks_input_validation(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["component_input_refs"][1]["required_model_surfaces"] = ["model_04_unified_decision"]

        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertFalse(result["valid"])
        self.assertIn(
            "component_input_refs[1].required_model_surfaces mismatch for component_02_entry",
            result["row_errors"],
        )

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

    def test_route_plan_validation_rechecks_component_identity_and_model_surfaces(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})
        plan["component_routes"][-1]["component_step"] = "C08"
        plan["component_routes"][1]["required_model_surfaces"] = ["model_04_unified_decision"]

        validation = validate_realtime_decision_route_plan(plan)

        self.assertFalse(validation["valid"])
        self.assertIn("component_routes[6].component_step mismatch for component_07_failure_review", validation["row_errors"])
        self.assertIn(
            "component_routes[1].required_model_surfaces mismatch for component_02_entry",
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
            self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_runtime_component_route")

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

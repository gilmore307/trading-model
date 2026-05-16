from __future__ import annotations

import json
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
    layers = [
        ("layer_01_market_regime", "model_01_market_regime", "market_context_state"),
        ("layer_02_sector_context", "model_02_sector_context", "sector_context_state"),
        ("layer_03_target_state_vector", "model_03_target_state_vector", "target_context_state"),
        ("layer_08_event_risk_governor", "model_08_event_risk_governor", "event_context_vector"),
        ("layer_05_alpha_confidence", "model_05_alpha_confidence", "alpha_confidence_vector"),
        ("layer_06_position_projection", "model_06_position_projection", "position_projection_vector"),
        ("layer_07_underlying_action", "model_07_underlying_action", "underlying_action_plan"),
        ("layer_08_option_expression", "model_08_option_expression", "option_expression_plan"),
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
        "layer_input_refs": [
            {
                "contract_type": "execution_model_decision_layer_input",
                "decision_input_snapshot_id": "rtdecision_unit",
                "model_layer": layer,
                "model_id": model_id,
                "expected_model_output": output,
                "feature_ref": f"realtime-feature://rtfeat_unit/{layer}",
                "upstream_context_refs": [f"placeholder://upstream/{layer}"],
                "frozen_model_config_ref": "trading-model://configs/frozen/unit",
                "historical_dataset_snapshot_ref": "trading-model://snapshots/historical/unit",
                "realtime_feature_snapshot_ref": "realtime-feature-snapshot://rtfeat_unit",
                "decision_handoff_status": "ready_for_historical_model_decision_input",
            }
            for layer, model_id, output in layers
        ],
    }


class RealtimeDecisionHandoffTests(unittest.TestCase):
    def test_validate_execution_input_requires_all_layers(self) -> None:
        snapshot = _decision_input_snapshot()
        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_layers"], [])
        self.assertEqual(result["provider_calls_performed"], 0)
        self.assertFalse(result["model_activation_performed"])

    def test_build_route_plan_maps_all_layers_to_generators(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})

        self.assertEqual(plan["contract_type"], "model_realtime_decision_route_plan")
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_historical_model_decision_route")
        self.assertEqual(len(plan["layer_routes"]), 8)
        self.assertEqual(plan["provider_calls_performed"], 0)
        self.assertFalse(plan["model_activation_performed"])
        self.assertFalse(plan["broker_order_construction_performed"])
        layer_8 = plan["layer_routes"][-1]
        self.assertEqual(layer_8["model_layer"], "layer_08_option_expression")
        self.assertIn("generate_model_08_option_expression.py", layer_8["generator_entrypoint_ref"])
        validation = validate_realtime_decision_route_plan(plan)
        self.assertTrue(validation["valid"])

    def test_forbidden_model_activation_blocks_input_validation(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["requested_actions"] = ["model_activation"]

        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertFalse(result["valid"])
        self.assertIn("model_activation", result["forbidden_actions_present"])

    def test_cli_plans_and_validates_route_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "decision_input.json"
            plan_path = Path(temp_dir) / "route_plan.json"
            input_path.write_text(json.dumps(_decision_input_snapshot()), encoding="utf-8")

            plan_result = subprocess.run(
                [sys.executable, "scripts/models/plan_realtime_decision_handoff.py", str(input_path)],
                check=True,
                cwd="/root/projects/trading-model",
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )
            plan = json.loads(plan_result.stdout)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_historical_model_decision_route")

            validate_result = subprocess.run(
                [sys.executable, "scripts/models/validate_realtime_decision_handoff.py", str(plan_path)],
                check=True,
                cwd="/root/projects/trading-model",
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )
            validation = json.loads(validate_result.stdout)
            self.assertTrue(validation["valid"])
            self.assertFalse(validation["model_activation_performed"])


if __name__ == "__main__":
    unittest.main()

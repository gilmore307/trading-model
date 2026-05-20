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
    layers = [
        ("layer_01_market_regime", "market_regime_model", "market_context_state"),
        ("layer_02_sector_context", "sector_context_model", "sector_context_state"),
        ("layer_03_target_state_vector", "target_state_vector_model", "target_context_state"),
        ("layer_04_event_failure_risk", "event_failure_risk_model", "event_failure_risk_vector"),
        ("layer_05_alpha_confidence", "alpha_confidence_model", "alpha_confidence_vector"),
        ("layer_06_dynamic_risk_policy", "dynamic_risk_policy_model", "dynamic_risk_policy_state"),
        ("layer_07_position_projection", "position_projection_model", "position_projection_vector"),
        ("layer_08_underlying_action", "underlying_action_model", "underlying_action_plan"),
        ("layer_09_option_expression", "option_expression_model", "trading_guidance_record"),
        ("layer_10_event_risk_governor", "event_risk_governor", "event_context_vector"),
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
    def test_validate_execution_input_requires_all_required_layers(self) -> None:
        snapshot = _decision_input_snapshot()
        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_layers"], [])
        self.assertEqual(result["provider_calls_performed"], 0)
        self.assertFalse(result["model_activation_performed"])

    def test_layer_nine_option_expression_subset_is_optional_for_direct_underlying_route(self) -> None:
        snapshot = _decision_input_snapshot()
        snapshot["instrument_ref"] = "BTC-USD"
        snapshot["asset_expression_route"] = "direct_underlying_only"
        snapshot["layer_input_refs"] = [
            row for row in snapshot["layer_input_refs"] if row["model_layer"] != "layer_09_option_expression"
        ]

        result = validate_execution_model_decision_input_snapshot(snapshot)
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": snapshot})
        validation = validate_realtime_decision_route_plan(plan)

        self.assertTrue(result["valid"], result["row_errors"])
        self.assertEqual(result["missing_layers"], [])
        self.assertEqual(result["missing_optional_layers"], ["layer_09_option_expression"])
        self.assertEqual(len(plan["layer_routes"]), 9)
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_historical_model_decision_route")
        self.assertTrue(validation["valid"], validation["row_errors"])
        self.assertEqual(validation["missing_optional_layers"], ["layer_09_option_expression"])

    def test_layer_nine_option_expression_plan_output_is_still_accepted(self) -> None:
        snapshot = _decision_input_snapshot()
        for row in snapshot["layer_input_refs"]:
            if row["model_layer"] == "layer_09_option_expression":
                row["expected_model_output"] = "option_expression_plan"

        result = validate_execution_model_decision_input_snapshot(snapshot)

        self.assertTrue(result["valid"], result["row_errors"])

    def test_build_route_plan_maps_all_layers_to_generators(self) -> None:
        plan = build_realtime_decision_route_plan({"decision_input_snapshot": _decision_input_snapshot()})

        self.assertEqual(plan["contract_type"], "model_realtime_decision_route_plan")
        self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_historical_model_decision_route")
        self.assertEqual(len(plan["layer_routes"]), 10)
        self.assertEqual(plan["provider_calls_performed"], 0)
        self.assertFalse(plan["model_activation_performed"])
        self.assertFalse(plan["broker_order_construction_performed"])
        layer_4 = plan["layer_routes"][3]
        self.assertEqual(layer_4["model_layer"], "layer_04_event_failure_risk")
        self.assertIn("generate_model_04_event_failure_risk.py", layer_4["generator_entrypoint_ref"])
        layer_6 = plan["layer_routes"][5]
        self.assertEqual(layer_6["model_layer"], "layer_06_dynamic_risk_policy")
        self.assertEqual(layer_6["expected_model_output"], "dynamic_risk_policy_state")
        self.assertIn("generate_model_06_dynamic_risk_policy.py", layer_6["generator_entrypoint_ref"])
        layer_9 = plan["layer_routes"][-1]
        self.assertEqual(layer_9["model_layer"], "layer_10_event_risk_governor")
        self.assertEqual(layer_9["expected_model_output"], "event_context_vector")
        self.assertIn("generate_model_10_event_risk_governor.py", layer_9["generator_entrypoint_ref"])
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
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
            )
            plan = json.loads(plan_result.stdout)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan["readiness_status"], "ready_for_fixture_shadow_historical_model_decision_route")

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

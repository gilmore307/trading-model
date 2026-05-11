"""Realtime-to-model decision handoff planning.

This module consumes the execution-side
``execution_model_decision_input_snapshot_v1`` envelope and turns it into a
model-side route plan for fixture/shadow historical-model decision routing. It
validates shape and layer coverage only. It does not run model generators,
activate production configs, persist outputs, call providers, or authorize
execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

MODEL_LAYER_ORDER = (
    "layer_01_market_regime",
    "layer_02_sector_context",
    "layer_03_target_state_vector",
    "layer_04_event_overlay",
    "layer_05_alpha_confidence",
    "layer_06_position_projection",
    "layer_07_underlying_action",
    "layer_08_option_expression",
)

_LAYER_METADATA = {
    "layer_01_market_regime": {
        "model_id": "model_01_market_regime",
        "expected_model_output": "market_context_state",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_01_market_regime/generate_model_01_market_regime.py",
    },
    "layer_02_sector_context": {
        "model_id": "model_02_sector_context",
        "expected_model_output": "sector_context_state",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_02_sector_context/generate_model_02_sector_context.py",
    },
    "layer_03_target_state_vector": {
        "model_id": "model_03_target_state_vector",
        "expected_model_output": "target_context_state",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_03_target_state_vector/generate_model_03_target_state_vector.py",
    },
    "layer_04_event_overlay": {
        "model_id": "model_04_event_overlay",
        "expected_model_output": "event_context_vector",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_04_event_overlay/generate_model_04_event_overlay.py",
    },
    "layer_05_alpha_confidence": {
        "model_id": "model_05_alpha_confidence",
        "expected_model_output": "alpha_confidence_vector",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_05_alpha_confidence/generate_model_05_alpha_confidence.py",
    },
    "layer_06_position_projection": {
        "model_id": "model_06_position_projection",
        "expected_model_output": "position_projection_vector",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_06_position_projection/generate_model_06_position_projection.py",
    },
    "layer_07_underlying_action": {
        "model_id": "model_07_underlying_action",
        "expected_model_output": "underlying_action_plan",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_07_underlying_action/generate_model_07_underlying_action.py",
    },
    "layer_08_option_expression": {
        "model_id": "model_08_option_expression",
        "expected_model_output": "option_expression_plan",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_08_option_expression/generate_model_08_option_expression.py",
    },
}

FORBIDDEN_HANDOFF_ACTIONS = (
    "provider_stream_activation",
    "historical_snapshot_rewrite",
    "model_refit_before_reviewed_snapshot_boundary",
    "model_activation",
    "live_model_inference_activation",
    "production_decision_activation",
    "broker_order_construction",
    "broker_order_mutation",
    "account_mutation",
)

ACCEPTED_HANDOFF_MODES = ("fixture_replay", "shadow_monitoring")


@dataclass(frozen=True)
class RealtimeDecisionLayerRoute:
    """One model-layer route row prepared from execution input refs."""

    contract_type: str
    route_plan_id: str
    model_layer: str
    model_id: str
    expected_model_output: str
    feature_ref: str
    upstream_context_refs: tuple[str, ...]
    frozen_model_config_ref: str
    historical_dataset_snapshot_ref: str
    generator_entrypoint_ref: str
    generation_mode: str
    route_status: str

    def summary_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["upstream_context_refs"] = list(self.upstream_context_refs)
        return row


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def validate_execution_model_decision_input_snapshot(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the execution-side decision input envelope for model routing."""

    required = {
        "contract_type",
        "decision_input_snapshot_id",
        "decision_time",
        "instrument_ref",
        "dataset_role",
        "historical_dataset_snapshot_ref",
        "frozen_model_config_ref",
        "realtime_feature_snapshot_ref",
        "layer_input_refs",
    }
    present = {key for key, value in candidate.items() if value not in (None, "", [], {})}
    missing_fields = sorted(required - present)
    contract_type_valid = candidate.get("contract_type") == "execution_model_decision_input_snapshot_v1"
    decision_time_valid = _parse_time(candidate.get("decision_time")) is not None
    requested_actions = set(candidate.get("requested_actions") or [])
    forbidden_actions_present = sorted(requested_actions.intersection(FORBIDDEN_HANDOFF_ACTIONS))
    rows = candidate.get("layer_input_refs") or []
    row_errors: list[str] = []
    rows_by_layer: dict[str, Mapping[str, Any]] = {}

    if not _is_sequence(rows):
        row_errors.append("layer_input_refs must be a list")
    else:
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                row_errors.append(f"layer_input_refs[{index}] must be an object")
                continue
            layer = str(row.get("model_layer") or "")
            if layer in rows_by_layer:
                row_errors.append(f"duplicate layer input for {layer}")
            if layer:
                rows_by_layer[layer] = row
            metadata = _LAYER_METADATA.get(layer)
            if metadata is None:
                row_errors.append(f"layer_input_refs[{index}].model_layer unknown: {layer}")
                continue
            for field in ("model_id", "expected_model_output", "feature_ref", "frozen_model_config_ref", "historical_dataset_snapshot_ref"):
                if not row.get(field):
                    row_errors.append(f"layer_input_refs[{index}].{field} missing")
            if row.get("model_id") and row.get("model_id") != metadata["model_id"]:
                row_errors.append(f"layer_input_refs[{index}].model_id mismatch for {layer}")
            if row.get("expected_model_output") and row.get("expected_model_output") != metadata["expected_model_output"]:
                row_errors.append(f"layer_input_refs[{index}].expected_model_output mismatch for {layer}")

    missing_layers = sorted(set(MODEL_LAYER_ORDER) - set(rows_by_layer))
    valid = (
        not missing_fields
        and contract_type_valid
        and decision_time_valid
        and not forbidden_actions_present
        and not row_errors
        and not missing_layers
    )
    return {
        "contract_type": "model_realtime_decision_input_validation_v1",
        "decision_input_snapshot_id": candidate.get("decision_input_snapshot_id"),
        "valid": valid,
        "missing_fields": missing_fields,
        "contract_type_valid": contract_type_valid,
        "decision_time_valid": decision_time_valid,
        "forbidden_actions_present": forbidden_actions_present,
        "missing_layers": missing_layers,
        "row_errors": row_errors,
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "broker_calls_performed": 0,
        "account_mutation_performed": False,
    }


def build_realtime_decision_route_plan(request: Mapping[str, Any]) -> dict[str, Any]:
    """Build a model-side route plan from an execution decision input snapshot."""

    snapshot = request.get("decision_input_snapshot") or request
    if not isinstance(snapshot, Mapping):
        raise ValueError("decision_input_snapshot must be an object")
    validation = validate_execution_model_decision_input_snapshot(snapshot)
    mode = str(request.get("handoff_mode") or request.get("mode") or "shadow_monitoring")
    if mode not in ACCEPTED_HANDOFF_MODES:
        raise ValueError(f"handoff_mode must be one of {', '.join(ACCEPTED_HANDOFF_MODES)}")

    route_plan_id = str(
        request.get("route_plan_id")
        or _stable_id(
            "rtdroute",
            {
                "decision_input_snapshot_id": snapshot.get("decision_input_snapshot_id"),
                "decision_time": snapshot.get("decision_time"),
                "instrument_ref": snapshot.get("instrument_ref"),
                "mode": mode,
            },
        )
    )
    rows_by_layer = {
        str(row.get("model_layer")): row
        for row in snapshot.get("layer_input_refs", [])
        if isinstance(row, Mapping) and row.get("model_layer")
    }
    routes: list[RealtimeDecisionLayerRoute] = []
    for layer in MODEL_LAYER_ORDER:
        row = rows_by_layer.get(layer)
        if not row:
            continue
        metadata = _LAYER_METADATA[layer]
        routes.append(
            RealtimeDecisionLayerRoute(
                contract_type="model_realtime_decision_layer_route_v1",
                route_plan_id=route_plan_id,
                model_layer=layer,
                model_id=metadata["model_id"],
                expected_model_output=metadata["expected_model_output"],
                feature_ref=str(row.get("feature_ref") or ""),
                upstream_context_refs=tuple(row.get("upstream_context_refs") or ()),
                frozen_model_config_ref=str(row.get("frozen_model_config_ref") or snapshot.get("frozen_model_config_ref") or ""),
                historical_dataset_snapshot_ref=str(
                    row.get("historical_dataset_snapshot_ref") or snapshot.get("historical_dataset_snapshot_ref") or ""
                ),
                generator_entrypoint_ref=metadata["generator_entrypoint_ref"],
                generation_mode=mode,
                route_status="ready_for_fixture_shadow_generation" if validation["valid"] else "blocked_input_validation_failed",
            )
        )

    ready = validation["valid"] and len(routes) == len(MODEL_LAYER_ORDER)
    return {
        "contract_type": "model_realtime_decision_route_plan_v1",
        "route_plan_id": route_plan_id,
        "decision_input_snapshot_id": snapshot.get("decision_input_snapshot_id"),
        "decision_time": snapshot.get("decision_time"),
        "instrument_ref": snapshot.get("instrument_ref"),
        "handoff_mode": mode,
        "input_validation": validation,
        "layer_routes": [route.summary_row() for route in routes],
        "readiness_status": "ready_for_fixture_shadow_historical_model_decision_route" if ready else "blocked_realtime_decision_input_validation",
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "production_decision_activation_performed": False,
        "broker_calls_performed": 0,
        "broker_order_construction_performed": False,
        "account_mutation_performed": False,
        "boundary_note": (
            "This plan validates and routes refs only. It does not execute model generators, activate production "
            "configs, persist outputs, call providers, construct broker orders, or mutate accounts."
        ),
    }


def validate_realtime_decision_route_plan(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the model-side realtime decision route plan."""

    required = {
        "contract_type",
        "route_plan_id",
        "decision_input_snapshot_id",
        "decision_time",
        "instrument_ref",
        "handoff_mode",
        "input_validation",
        "layer_routes",
    }
    present = {key for key, value in candidate.items() if value not in (None, "", [], {})}
    missing_fields = sorted(required - present)
    contract_type_valid = candidate.get("contract_type") == "model_realtime_decision_route_plan_v1"
    handoff_mode_valid = candidate.get("handoff_mode") in ACCEPTED_HANDOFF_MODES
    input_validation = candidate.get("input_validation") or {}
    input_valid = bool(input_validation.get("valid")) if isinstance(input_validation, Mapping) else False
    routes = candidate.get("layer_routes") or []
    row_errors: list[str] = []
    layer_set: set[str] = set()
    if not _is_sequence(routes):
        row_errors.append("layer_routes must be a list")
    else:
        for index, row in enumerate(routes):
            if not isinstance(row, Mapping):
                row_errors.append(f"layer_routes[{index}] must be an object")
                continue
            layer = str(row.get("model_layer") or "")
            metadata = _LAYER_METADATA.get(layer)
            if metadata is None:
                row_errors.append(f"layer_routes[{index}].model_layer unknown: {layer}")
                continue
            layer_set.add(layer)
            for field in ("model_id", "expected_model_output", "feature_ref", "generator_entrypoint_ref", "generation_mode"):
                if not row.get(field):
                    row_errors.append(f"layer_routes[{index}].{field} missing")
            if row.get("generator_entrypoint_ref") != metadata["generator_entrypoint_ref"]:
                row_errors.append(f"layer_routes[{index}].generator_entrypoint_ref mismatch for {layer}")
    missing_layers = sorted(set(MODEL_LAYER_ORDER) - layer_set)
    valid = (
        not missing_fields
        and contract_type_valid
        and handoff_mode_valid
        and input_valid
        and not row_errors
        and not missing_layers
    )
    return {
        "contract_type": "model_realtime_decision_route_plan_validation_v1",
        "route_plan_id": candidate.get("route_plan_id"),
        "valid": valid,
        "missing_fields": missing_fields,
        "contract_type_valid": contract_type_valid,
        "handoff_mode_valid": handoff_mode_valid,
        "input_valid": input_valid,
        "missing_layers": missing_layers,
        "row_errors": row_errors,
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "production_decision_activation_performed": False,
        "broker_calls_performed": 0,
    }


__all__ = [
    "ACCEPTED_HANDOFF_MODES",
    "FORBIDDEN_HANDOFF_ACTIONS",
    "MODEL_LAYER_ORDER",
    "RealtimeDecisionLayerRoute",
    "build_realtime_decision_route_plan",
    "validate_execution_model_decision_input_snapshot",
    "validate_realtime_decision_route_plan",
]

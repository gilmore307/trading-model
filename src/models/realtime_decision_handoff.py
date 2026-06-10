"""Realtime/replay execution-component handoff planning.

This module consumes the execution-side
``execution_model_decision_input_snapshot`` envelope and turns it into a
model-side route plan for fixture/shadow routing through the accepted
execution runtime components. It validates shape and C01-C07 component
coverage only. It does not run model generators, activate production configs,
persist outputs, call providers, or authorize execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

RUNTIME_COMPONENT_ORDER = (
    "component_01_intake",
    "component_02_entry",
    "component_03_lifecycle",
    "component_04_option_review",
    "component_05_order_intent",
    "component_06_execution_gate",
    "component_07_failure_review",
)
REQUIRED_RUNTIME_COMPONENT_ORDER = (
    "component_01_intake",
    "component_02_entry",
    "component_03_lifecycle",
    "component_05_order_intent",
    "component_06_execution_gate",
)
OPTIONAL_RUNTIME_COMPONENT_ORDER = (
    "component_04_option_review",
    "component_07_failure_review",
)

_MODEL_ENTRYPOINTS = {
    "model_01_background_context": "trading-model/scripts/models/model_01_background_context/generate_model_01_background_context.py",
    "model_02_target_state": "trading-model/scripts/models/model_02_target_state/generate_model_02_target_state.py",
    "model_03_event_state": "trading-model/scripts/models/model_03_event_state/generate_model_03_event_state.py",
    "model_04_unified_decision": "trading-model/scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py",
    "model_05_option_expression": "trading-model/scripts/models/model_05_option_expression/generate_model_05_option_expression.py",
    "model_06_residual_event_governance": (
        "trading-model/scripts/models/model_06_residual_event_governance/"
        "generate_model_06_residual_event_governance.py"
    ),
}

_COMPONENT_METADATA = {
    "component_01_intake": {
        "component_step": "C01",
        "component_name": "Intake",
        "required_model_surfaces": ("model_01_background_context", "model_02_target_state"),
        "optional_model_surfaces": (),
        "input_contracts": (
            "background_context_state",
            "target_context_state",
            "account_sleeve_state_snapshot",
            "position_state_snapshot",
        ),
        "output_contracts": ("execution_intake_snapshot",),
        "invocation_policy": "required_runtime_component",
    },
    "component_02_entry": {
        "component_step": "C02",
        "component_name": "Entry",
        "required_model_surfaces": ("model_03_event_state", "model_04_unified_decision"),
        "optional_model_surfaces": ("model_06_residual_event_governance",),
        "input_contracts": ("execution_intake_snapshot", "event_state_vector", "unified_decision_vector"),
        "output_contracts": ("entry_decision",),
        "invocation_policy": "required_runtime_component_for_candidate_entries",
    },
    "component_03_lifecycle": {
        "component_step": "C03",
        "component_name": "Lifecycle",
        "required_model_surfaces": ("model_03_event_state", "model_04_unified_decision"),
        "optional_model_surfaces": ("model_06_residual_event_governance",),
        "input_contracts": ("position_state_snapshot", "event_state_vector", "unified_decision_vector"),
        "output_contracts": ("position_lifecycle_decision",),
        "invocation_policy": "required_runtime_component_for_open_positions",
    },
    "component_04_option_review": {
        "component_step": "C04",
        "component_name": "Option Review",
        "required_model_surfaces": (),
        "optional_model_surfaces": ("model_05_option_expression", "model_06_residual_event_governance"),
        "input_contracts": ("unified_decision_vector", "option_expression_plan"),
        "output_contracts": ("option_reexpression_decision",),
        "invocation_policy": "conditional_for_optionable_routes_or_held_options",
    },
    "component_05_order_intent": {
        "component_step": "C05",
        "component_name": "Order Intent",
        "required_model_surfaces": (),
        "optional_model_surfaces": (),
        "input_contracts": (
            "entry_decision",
            "position_lifecycle_decision",
            "option_reexpression_decision",
            "trade_risk_cap",
        ),
        "output_contracts": ("execution_order_intent",),
        "invocation_policy": "required_after_accepted_entry_lifecycle_or_option_decision",
    },
    "component_06_execution_gate": {
        "component_step": "C06",
        "component_name": "Execution Gate",
        "required_model_surfaces": (),
        "optional_model_surfaces": (),
        "input_contracts": ("execution_order_intent", "agent_final_review"),
        "output_contracts": ("execution_gate_result",),
        "invocation_policy": "required_before_live_or_replay_execution_adapter",
    },
    "component_07_failure_review": {
        "component_step": "C07",
        "component_name": "Failure Review",
        "required_model_surfaces": (),
        "optional_model_surfaces": ("model_06_residual_event_governance",),
        "input_contracts": ("observed_model_or_trade_failure", "event_risk_intervention"),
        "output_contracts": ("failure_explanation_packet",),
        "invocation_policy": "conditional_after_observed_failure_deviation_or_residual_event_risk",
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
ACCEPTED_DATASET_ROLES = ("fixture_replay", "forward_holdout", "shadow_monitoring")


@dataclass(frozen=True)
class RealtimeDecisionComponentRoute:
    """One C-runtime component route prepared from execution input refs."""

    contract_type: str
    route_plan_id: str
    component_id: str
    component_step: str
    component_name: str
    required_model_surfaces: tuple[str, ...]
    optional_model_surfaces: tuple[str, ...]
    input_contracts: tuple[str, ...]
    output_contracts: tuple[str, ...]
    feature_ref: str
    upstream_context_refs: tuple[str, ...]
    frozen_model_config_ref: str
    historical_dataset_snapshot_ref: str
    model_entrypoint_refs: tuple[str, ...]
    invocation_policy: str
    generation_mode: str
    route_status: str

    def summary_row(self) -> dict[str, Any]:
        row = asdict(self)
        for field in (
            "required_model_surfaces",
            "optional_model_surfaces",
            "input_contracts",
            "output_contracts",
            "upstream_context_refs",
            "model_entrypoint_refs",
        ):
            row[field] = list(row[field])
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


def _component_input_rows(candidate: Mapping[str, Any]) -> Any:
    return candidate.get("component_input_refs")


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    return tuple(str(item) for item in value if str(item))


def validate_execution_model_decision_input_snapshot(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the execution-side decision input envelope for C-component routing."""

    required = {
        "contract_type",
        "decision_input_snapshot_id",
        "decision_time",
        "instrument_ref",
        "dataset_role",
        "historical_dataset_snapshot_ref",
        "frozen_model_config_ref",
        "realtime_feature_snapshot_ref",
        "component_input_refs",
    }
    present = {key for key, value in candidate.items() if value not in (None, "", [], {})}
    missing_fields = sorted(required - present)
    contract_type_valid = candidate.get("contract_type") == "execution_model_decision_input_snapshot"
    decision_time_valid = _parse_time(candidate.get("decision_time")) is not None
    dataset_role = str(candidate.get("dataset_role") or "")
    dataset_role_valid = dataset_role in ACCEPTED_DATASET_ROLES
    requested_actions = set(candidate.get("requested_actions") or [])
    forbidden_actions_present = sorted(requested_actions.intersection(FORBIDDEN_HANDOFF_ACTIONS))
    rows = _component_input_rows(candidate) or []
    row_errors: list[str] = []
    rows_by_component: dict[str, Mapping[str, Any]] = {}

    if not _is_sequence(rows):
        row_errors.append("component_input_refs must be a list")
    else:
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                row_errors.append(f"component_input_refs[{index}] must be an object")
                continue
            component = str(row.get("component_id") or row.get("model_component") or "")
            if component in rows_by_component:
                row_errors.append(f"duplicate component input for {component}")
            if component:
                rows_by_component[component] = row
            metadata = _COMPONENT_METADATA.get(component)
            if metadata is None:
                row_errors.append(f"component_input_refs[{index}].component_id unknown: {component}")
                continue
            for field in ("feature_ref", "frozen_model_config_ref", "historical_dataset_snapshot_ref"):
                if not row.get(field):
                    row_errors.append(f"component_input_refs[{index}].{field} missing")
            if row.get("component_step") and row.get("component_step") != metadata["component_step"]:
                row_errors.append(f"component_input_refs[{index}].component_step mismatch for {component}")
            if row.get("component_name") and row.get("component_name") != metadata["component_name"]:
                row_errors.append(f"component_input_refs[{index}].component_name mismatch for {component}")
            expected_required = tuple(metadata["required_model_surfaces"])
            provided_required = _tuple_of_strings(row.get("required_model_surfaces"))
            if provided_required and provided_required != expected_required:
                row_errors.append(f"component_input_refs[{index}].required_model_surfaces mismatch for {component}")
            expected_optional = tuple(metadata["optional_model_surfaces"])
            provided_optional = _tuple_of_strings(row.get("optional_model_surfaces"))
            if provided_optional and provided_optional != expected_optional:
                row_errors.append(f"component_input_refs[{index}].optional_model_surfaces mismatch for {component}")

    missing_components = sorted(set(REQUIRED_RUNTIME_COMPONENT_ORDER) - set(rows_by_component))
    missing_optional_components = sorted(set(OPTIONAL_RUNTIME_COMPONENT_ORDER) - set(rows_by_component))
    valid = (
        not missing_fields
        and contract_type_valid
        and decision_time_valid
        and dataset_role_valid
        and not forbidden_actions_present
        and not row_errors
        and not missing_components
    )
    return {
        "contract_type": "model_realtime_decision_input_validation",
        "decision_input_snapshot_id": candidate.get("decision_input_snapshot_id"),
        "valid": valid,
        "missing_fields": missing_fields,
        "contract_type_valid": contract_type_valid,
        "decision_time_valid": decision_time_valid,
        "dataset_role_valid": dataset_role_valid,
        "forbidden_actions_present": forbidden_actions_present,
        "missing_components": missing_components,
        "missing_optional_components": missing_optional_components,
        "row_errors": row_errors,
        "execution_unit": "runtime_component",
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "broker_calls_performed": 0,
        "account_mutation_performed": False,
    }


def build_realtime_decision_route_plan(request: Mapping[str, Any]) -> dict[str, Any]:
    """Build a model-side C-component route plan from an execution snapshot."""

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
    rows_by_component = {
        str(row.get("component_id") or row.get("model_component")): row
        for row in _component_input_rows(snapshot) or []
        if isinstance(row, Mapping) and (row.get("component_id") or row.get("model_component"))
    }
    routes: list[RealtimeDecisionComponentRoute] = []
    for component in RUNTIME_COMPONENT_ORDER:
        row = rows_by_component.get(component)
        if not row:
            continue
        metadata = _COMPONENT_METADATA[component]
        model_surfaces = tuple(metadata["required_model_surfaces"]) + tuple(metadata["optional_model_surfaces"])
        routes.append(
            RealtimeDecisionComponentRoute(
                contract_type="model_realtime_decision_component_route",
                route_plan_id=route_plan_id,
                component_id=component,
                component_step=metadata["component_step"],
                component_name=metadata["component_name"],
                required_model_surfaces=tuple(metadata["required_model_surfaces"]),
                optional_model_surfaces=tuple(metadata["optional_model_surfaces"]),
                input_contracts=tuple(metadata["input_contracts"]),
                output_contracts=tuple(metadata["output_contracts"]),
                feature_ref=str(row.get("feature_ref") or ""),
                upstream_context_refs=tuple(row.get("upstream_context_refs") or ()),
                frozen_model_config_ref=str(row.get("frozen_model_config_ref") or snapshot.get("frozen_model_config_ref") or ""),
                historical_dataset_snapshot_ref=str(
                    row.get("historical_dataset_snapshot_ref") or snapshot.get("historical_dataset_snapshot_ref") or ""
                ),
                model_entrypoint_refs=tuple(_MODEL_ENTRYPOINTS[surface] for surface in model_surfaces),
                invocation_policy=metadata["invocation_policy"],
                generation_mode=mode,
                route_status="ready_for_fixture_shadow_generation" if validation["valid"] else "blocked_input_validation_failed",
            )
        )

    routed_components = {route.component_id for route in routes}
    ready = validation["valid"] and set(REQUIRED_RUNTIME_COMPONENT_ORDER).issubset(routed_components)
    return {
        "contract_type": "model_realtime_decision_route_plan",
        "route_plan_id": route_plan_id,
        "decision_input_snapshot_id": snapshot.get("decision_input_snapshot_id"),
        "decision_time": snapshot.get("decision_time"),
        "instrument_ref": snapshot.get("instrument_ref"),
        "handoff_mode": mode,
        "execution_unit": "runtime_component",
        "input_validation": validation,
        "component_routes": [route.summary_row() for route in routes],
        "readiness_status": "ready_for_fixture_shadow_runtime_component_route" if ready else "blocked_realtime_decision_input_validation",
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "production_decision_activation_performed": False,
        "broker_calls_performed": 0,
        "broker_order_construction_performed": False,
        "account_mutation_performed": False,
        "boundary_note": (
            "This plan validates and routes accepted execution runtime component refs only. It does not execute model "
            "generators, activate production configs, persist outputs, call providers, construct broker orders, or "
            "mutate accounts."
        ),
    }


def validate_realtime_decision_route_plan(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the model-side realtime/replay C-component route plan."""

    required = {
        "contract_type",
        "route_plan_id",
        "decision_input_snapshot_id",
        "decision_time",
        "instrument_ref",
        "handoff_mode",
        "execution_unit",
        "input_validation",
        "component_routes",
    }
    present = {key for key, value in candidate.items() if value not in (None, "", [], {})}
    missing_fields = sorted(required - present)
    contract_type_valid = candidate.get("contract_type") == "model_realtime_decision_route_plan"
    handoff_mode_valid = candidate.get("handoff_mode") in ACCEPTED_HANDOFF_MODES
    execution_unit_valid = candidate.get("execution_unit") == "runtime_component"
    input_validation = candidate.get("input_validation") or {}
    input_valid = bool(input_validation.get("valid")) if isinstance(input_validation, Mapping) else False
    routes = candidate.get("component_routes") or []
    row_errors: list[str] = []
    component_set: set[str] = set()
    if not _is_sequence(routes):
        row_errors.append("component_routes must be a list")
    else:
        for index, row in enumerate(routes):
            if not isinstance(row, Mapping):
                row_errors.append(f"component_routes[{index}] must be an object")
                continue
            component = str(row.get("component_id") or "")
            metadata = _COMPONENT_METADATA.get(component)
            if metadata is None:
                row_errors.append(f"component_routes[{index}].component_id unknown: {component}")
                continue
            component_set.add(component)
            for field in (
                "component_step",
                "component_name",
                "required_model_surfaces",
                "optional_model_surfaces",
                "input_contracts",
                "output_contracts",
                "feature_ref",
                "model_entrypoint_refs",
                "invocation_policy",
                "generation_mode",
            ):
                if field not in row or row.get(field) in (None, "", []):
                    if field in {"required_model_surfaces", "optional_model_surfaces", "model_entrypoint_refs"}:
                        continue
                    row_errors.append(f"component_routes[{index}].{field} missing")
            if row.get("component_step") and row.get("component_step") != metadata["component_step"]:
                row_errors.append(f"component_routes[{index}].component_step mismatch for {component}")
            if row.get("component_name") and row.get("component_name") != metadata["component_name"]:
                row_errors.append(f"component_routes[{index}].component_name mismatch for {component}")
            if _tuple_of_strings(row.get("required_model_surfaces")) != tuple(metadata["required_model_surfaces"]):
                row_errors.append(f"component_routes[{index}].required_model_surfaces mismatch for {component}")
            if _tuple_of_strings(row.get("optional_model_surfaces")) != tuple(metadata["optional_model_surfaces"]):
                row_errors.append(f"component_routes[{index}].optional_model_surfaces mismatch for {component}")
            expected_entrypoints = tuple(
                _MODEL_ENTRYPOINTS[surface]
                for surface in tuple(metadata["required_model_surfaces"]) + tuple(metadata["optional_model_surfaces"])
            )
            if _tuple_of_strings(row.get("model_entrypoint_refs")) != expected_entrypoints:
                row_errors.append(f"component_routes[{index}].model_entrypoint_refs mismatch for {component}")
    missing_components = sorted(set(REQUIRED_RUNTIME_COMPONENT_ORDER) - component_set)
    missing_optional_components = sorted(set(OPTIONAL_RUNTIME_COMPONENT_ORDER) - component_set)
    valid = (
        not missing_fields
        and contract_type_valid
        and handoff_mode_valid
        and execution_unit_valid
        and input_valid
        and not row_errors
        and not missing_components
    )
    return {
        "contract_type": "model_realtime_decision_route_plan_validation",
        "route_plan_id": candidate.get("route_plan_id"),
        "valid": valid,
        "missing_fields": missing_fields,
        "contract_type_valid": contract_type_valid,
        "handoff_mode_valid": handoff_mode_valid,
        "execution_unit_valid": execution_unit_valid,
        "input_valid": input_valid,
        "missing_components": missing_components,
        "missing_optional_components": missing_optional_components,
        "row_errors": row_errors,
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "production_decision_activation_performed": False,
        "broker_calls_performed": 0,
    }


__all__ = [
    "ACCEPTED_HANDOFF_MODES",
    "ACCEPTED_DATASET_ROLES",
    "FORBIDDEN_HANDOFF_ACTIONS",
    "OPTIONAL_RUNTIME_COMPONENT_ORDER",
    "REQUIRED_RUNTIME_COMPONENT_ORDER",
    "RUNTIME_COMPONENT_ORDER",
    "RealtimeDecisionComponentRoute",
    "build_realtime_decision_route_plan",
    "validate_execution_model_decision_input_snapshot",
    "validate_realtime_decision_route_plan",
]

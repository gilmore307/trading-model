"""Realtime/replay component handoff planning.

This module consumes the execution-side
``execution_model_decision_input_snapshot`` envelope and turns it into a
model-side component route plan for fixture/shadow routing. It validates shape
and current component coverage only. It does not run model generators, activate
production configs, persist outputs, call providers, or authorize execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

MODEL_COMPONENT_ORDER = (
    "background_context_component",
    "target_state_component",
    "event_state_component",
    "unified_decision_component",
    "option_expression_component",
    "residual_event_governance_component",
)
REQUIRED_MODEL_COMPONENT_ORDER = tuple(
    component for component in MODEL_COMPONENT_ORDER if component != "option_expression_component"
)
OPTIONAL_MODEL_COMPONENT_ORDER = ("option_expression_component",)

_COMPONENT_METADATA = {
    "background_context_component": {
        "model_step": "M01",
        "model_surface": "model_01_background_context",
        "model_id": "background_context_model",
        "expected_model_output": "background_context_state",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_01_background_context/generate_model_01_background_context.py",
        "invocation_policy": "required_component",
    },
    "target_state_component": {
        "model_step": "M02",
        "model_surface": "model_02_target_state",
        "model_id": "target_state_model",
        "expected_model_output": "target_context_state",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_02_target_state/generate_model_02_target_state.py",
        "invocation_policy": "required_component",
    },
    "event_state_component": {
        "model_step": "M03",
        "model_surface": "model_03_event_state",
        "model_id": "event_state_model",
        "expected_model_output": "event_state_vector",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_03_event_state/generate_model_03_event_state.py",
        "invocation_policy": "required_component",
    },
    "unified_decision_component": {
        "model_step": "M04",
        "model_surface": "model_04_unified_decision",
        "model_id": "unified_decision_model",
        "expected_model_output": "unified_decision_vector",
        "generator_entrypoint_ref": "trading-model/scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py",
        "invocation_policy": "required_decision_component",
    },
    "option_expression_component": {
        "model_step": "M05",
        "model_surface": "model_05_option_expression",
        "model_id": "option_expression_model",
        "expected_model_output": "option_expression_plan",
        "accepted_model_outputs": ("trading_guidance_record", "option_expression_plan", "expression_vector"),
        "generator_entrypoint_ref": "trading-model/scripts/models/model_05_option_expression/generate_model_05_option_expression.py",
        "invocation_policy": "conditional_after_unified_decision_or_option_applicability",
    },
    "residual_event_governance_component": {
        "model_step": "M06",
        "model_surface": "model_06_residual_event_governance",
        "model_id": "residual_event_governance_model",
        "expected_model_output": "event_risk_intervention",
        "generator_entrypoint_ref": (
            "trading-model/scripts/models/model_06_residual_event_governance/"
            "generate_model_06_residual_event_governance.py"
        ),
        "invocation_policy": "required_residual_event_governance_component",
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
    """One current model component route prepared from execution input refs."""

    contract_type: str
    route_plan_id: str
    model_component: str
    model_step: str
    model_surface: str
    model_id: str
    expected_model_output: str
    feature_ref: str
    upstream_context_refs: tuple[str, ...]
    frozen_model_config_ref: str
    historical_dataset_snapshot_ref: str
    generator_entrypoint_ref: str
    invocation_policy: str
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


def _component_input_rows(candidate: Mapping[str, Any]) -> Any:
    return candidate.get("component_input_refs")


def validate_execution_model_decision_input_snapshot(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the execution-side decision input envelope for component routing."""

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
            component = str(row.get("model_component") or "")
            if component in rows_by_component:
                row_errors.append(f"duplicate component input for {component}")
            if component:
                rows_by_component[component] = row
            metadata = _COMPONENT_METADATA.get(component)
            if metadata is None:
                row_errors.append(f"component_input_refs[{index}].model_component unknown: {component}")
                continue
            for field in (
                "model_id",
                "expected_model_output",
                "feature_ref",
                "frozen_model_config_ref",
                "historical_dataset_snapshot_ref",
            ):
                if not row.get(field):
                    row_errors.append(f"component_input_refs[{index}].{field} missing")
            if row.get("model_id") and row.get("model_id") != metadata["model_id"]:
                row_errors.append(f"component_input_refs[{index}].model_id mismatch for {component}")
            accepted_outputs = metadata.get("accepted_model_outputs") or (metadata["expected_model_output"],)
            if row.get("expected_model_output") and row.get("expected_model_output") not in accepted_outputs:
                row_errors.append(f"component_input_refs[{index}].expected_model_output mismatch for {component}")

    missing_components = sorted(set(REQUIRED_MODEL_COMPONENT_ORDER) - set(rows_by_component))
    missing_optional_components = sorted(set(OPTIONAL_MODEL_COMPONENT_ORDER) - set(rows_by_component))
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
        "execution_unit": "component",
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "broker_calls_performed": 0,
        "account_mutation_performed": False,
    }


def build_realtime_decision_route_plan(request: Mapping[str, Any]) -> dict[str, Any]:
    """Build a model-side component route plan from an execution snapshot."""

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
        str(row.get("model_component")): row
        for row in _component_input_rows(snapshot) or []
        if isinstance(row, Mapping) and row.get("model_component")
    }
    routes: list[RealtimeDecisionComponentRoute] = []
    for component in MODEL_COMPONENT_ORDER:
        row = rows_by_component.get(component)
        if not row:
            continue
        metadata = _COMPONENT_METADATA[component]
        routes.append(
            RealtimeDecisionComponentRoute(
                contract_type="model_realtime_decision_component_route",
                route_plan_id=route_plan_id,
                model_component=component,
                model_step=metadata["model_step"],
                model_surface=metadata["model_surface"],
                model_id=metadata["model_id"],
                expected_model_output=str(row.get("expected_model_output") or metadata["expected_model_output"]),
                feature_ref=str(row.get("feature_ref") or ""),
                upstream_context_refs=tuple(row.get("upstream_context_refs") or ()),
                frozen_model_config_ref=str(row.get("frozen_model_config_ref") or snapshot.get("frozen_model_config_ref") or ""),
                historical_dataset_snapshot_ref=str(
                    row.get("historical_dataset_snapshot_ref") or snapshot.get("historical_dataset_snapshot_ref") or ""
                ),
                generator_entrypoint_ref=metadata["generator_entrypoint_ref"],
                invocation_policy=metadata["invocation_policy"],
                generation_mode=mode,
                route_status="ready_for_fixture_shadow_generation" if validation["valid"] else "blocked_input_validation_failed",
            )
        )

    routed_components = {route.model_component for route in routes}
    ready = validation["valid"] and set(REQUIRED_MODEL_COMPONENT_ORDER).issubset(routed_components)
    return {
        "contract_type": "model_realtime_decision_route_plan",
        "route_plan_id": route_plan_id,
        "decision_input_snapshot_id": snapshot.get("decision_input_snapshot_id"),
        "decision_time": snapshot.get("decision_time"),
        "instrument_ref": snapshot.get("instrument_ref"),
        "handoff_mode": mode,
        "execution_unit": "component",
        "input_validation": validation,
        "component_routes": [route.summary_row() for route in routes],
        "readiness_status": "ready_for_fixture_shadow_component_route" if ready else "blocked_realtime_decision_input_validation",
        "provider_calls_performed": 0,
        "model_activation_performed": False,
        "production_decision_activation_performed": False,
        "broker_calls_performed": 0,
        "broker_order_construction_performed": False,
        "account_mutation_performed": False,
        "boundary_note": (
            "This plan validates and routes current model component refs only. It does not execute model generators, "
            "activate production configs, persist outputs, call providers, construct broker orders, or mutate accounts."
        ),
    }


def validate_realtime_decision_route_plan(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the model-side realtime/replay component route plan."""

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
    execution_unit_valid = candidate.get("execution_unit") == "component"
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
            component = str(row.get("model_component") or "")
            metadata = _COMPONENT_METADATA.get(component)
            if metadata is None:
                row_errors.append(f"component_routes[{index}].model_component unknown: {component}")
                continue
            component_set.add(component)
            for field in (
                "model_step",
                "model_surface",
                "model_id",
                "expected_model_output",
                "feature_ref",
                "generator_entrypoint_ref",
                "invocation_policy",
                "generation_mode",
            ):
                if not row.get(field):
                    row_errors.append(f"component_routes[{index}].{field} missing")
            if row.get("model_step") and row.get("model_step") != metadata["model_step"]:
                row_errors.append(f"component_routes[{index}].model_step mismatch for {component}")
            if row.get("model_surface") and row.get("model_surface") != metadata["model_surface"]:
                row_errors.append(f"component_routes[{index}].model_surface mismatch for {component}")
            if row.get("model_id") and row.get("model_id") != metadata["model_id"]:
                row_errors.append(f"component_routes[{index}].model_id mismatch for {component}")
            accepted_outputs = metadata.get("accepted_model_outputs") or (metadata["expected_model_output"],)
            if row.get("expected_model_output") and row.get("expected_model_output") not in accepted_outputs:
                row_errors.append(f"component_routes[{index}].expected_model_output mismatch for {component}")
            if row.get("generator_entrypoint_ref") != metadata["generator_entrypoint_ref"]:
                row_errors.append(f"component_routes[{index}].generator_entrypoint_ref mismatch for {component}")
    missing_components = sorted(set(REQUIRED_MODEL_COMPONENT_ORDER) - component_set)
    missing_optional_components = sorted(set(OPTIONAL_MODEL_COMPONENT_ORDER) - component_set)
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
    "MODEL_COMPONENT_ORDER",
    "OPTIONAL_MODEL_COMPONENT_ORDER",
    "REQUIRED_MODEL_COMPONENT_ORDER",
    "RealtimeDecisionComponentRoute",
    "build_realtime_decision_route_plan",
    "validate_execution_model_decision_input_snapshot",
    "validate_realtime_decision_route_plan",
]

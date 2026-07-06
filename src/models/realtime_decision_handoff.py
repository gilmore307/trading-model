"""Realtime/replay execution-component handoff planning.

This module consumes the execution-side
``execution_model_decision_input_snapshot`` envelope and turns it into a
model-side route plan for fixture/shadow routing through the accepted
execution runtime components. It validates shape and C01-C07 component
coverage only. It does not run model generators, activate production configs,
persist outputs, call providers, or authorize execution.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Sequence

RUNTIME_COMPONENT_ORDER = (
    "component_01_intake",
    "component_02_entry",
    "component_03_lifecycle",
    "component_04_expression_review",
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
    "component_04_expression_review",
    "component_07_failure_review",
)

_MODEL_ENTRYPOINTS = {
    "model_01_background_context": "trading-model/scripts/models/model_01_background_context/generate_model_01_background_context.py",
    "model_02_target_state": "trading-model/scripts/models/model_02_target_state/generate_model_02_target_state.py",
    "model_03_event_state": "trading-model/scripts/models/model_03_event_state/generate_model_03_event_state.py",
    "model_04_unified_decision": "trading-model/scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py",
    "model_05_option_expression": "trading-model/scripts/models/model_05_option_expression/generate_model_05_option_expression.py",
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
ACCEPTED_RUNTIME_COMPONENT_MANIFEST_VERSION = "2026-07-06"
ACCEPTED_RUNTIME_COMPONENT_MANIFEST_CHECKSUM = "137fa39c83684218"


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


def _manifest_checksum_valid(manifest: Mapping[str, Any]) -> bool:
    expected = str(manifest.get("manifest_checksum") or "")
    payload = dict(manifest)
    payload.pop("manifest_checksum", None)
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return bool(expected) and digest == expected


def _validate_runtime_component_manifest(manifest: Any) -> dict[str, Any]:
    """Validate the execution-owned runtime component manifest carried by the snapshot."""

    errors: list[str] = []
    if not isinstance(manifest, Mapping):
        return {
            "valid": False,
            "errors": ["runtime_component_manifest must be an object"],
            "component_order": (),
            "required_component_order": (),
            "optional_component_order": (),
            "components_by_id": {},
        }
    if manifest.get("contract_type") != "execution_runtime_component_manifest":
        errors.append("runtime_component_manifest contract_type invalid")
    if not manifest.get("manifest_version"):
        errors.append("runtime_component_manifest manifest_version missing")
    elif manifest.get("manifest_version") != ACCEPTED_RUNTIME_COMPONENT_MANIFEST_VERSION:
        errors.append("runtime_component_manifest manifest_version is not the accepted current version")
    if manifest.get("manifest_checksum") != ACCEPTED_RUNTIME_COMPONENT_MANIFEST_CHECKSUM:
        errors.append("runtime_component_manifest manifest_checksum is not the accepted current checksum")
    if not _manifest_checksum_valid(manifest):
        errors.append("runtime_component_manifest manifest_checksum invalid")
    component_order = _tuple_of_strings(manifest.get("component_order"))
    required_component_order = _tuple_of_strings(manifest.get("required_component_order"))
    optional_component_order = _tuple_of_strings(manifest.get("optional_component_order"))
    if not component_order:
        errors.append("runtime_component_manifest component_order missing")
    elif component_order != RUNTIME_COMPONENT_ORDER:
        errors.append("runtime_component_manifest component_order is not the accepted current order")
    if not required_component_order:
        errors.append("runtime_component_manifest required_component_order missing")
    elif required_component_order != REQUIRED_RUNTIME_COMPONENT_ORDER:
        errors.append("runtime_component_manifest required_component_order is not the accepted current required order")
    if optional_component_order != OPTIONAL_RUNTIME_COMPONENT_ORDER:
        errors.append("runtime_component_manifest optional_component_order is not the accepted current optional order")
    components = manifest.get("components") or []
    components_by_id: dict[str, Mapping[str, Any]] = {}
    if not _is_sequence(components):
        errors.append("runtime_component_manifest components must be a list")
    else:
        for index, row in enumerate(components):
            if not isinstance(row, Mapping):
                errors.append(f"runtime_component_manifest.components[{index}] must be an object")
                continue
            component_id = str(row.get("component_id") or "")
            if not component_id:
                errors.append(f"runtime_component_manifest.components[{index}].component_id missing")
                continue
            if component_id in components_by_id:
                errors.append(f"duplicate runtime component manifest row for {component_id}")
            components_by_id[component_id] = row
            for forbidden in ("called_model_layers", "event_risk_control_policy"):
                if forbidden in row:
                    errors.append(f"runtime_component_manifest.components[{index}].{forbidden} forbidden")
            for field in (
                "component_step",
                "component_name",
                "required_model_surfaces",
                "optional_model_surfaces",
                "input_contracts",
                "output_contracts",
                "live_invocation_policy",
                "replay_invocation_policy",
                "skip_degrade_policy",
            ):
                if field not in row:
                    errors.append(f"runtime_component_manifest.components[{index}].{field} missing")
            for surface in _tuple_of_strings(row.get("required_model_surfaces")) + _tuple_of_strings(
                row.get("optional_model_surfaces")
            ):
                if surface not in _MODEL_ENTRYPOINTS:
                    errors.append(f"runtime_component_manifest.components[{index}] unknown model surface {surface}")
    missing_component_manifest_rows = sorted(set(component_order) - set(components_by_id))
    if missing_component_manifest_rows:
        errors.append(f"runtime_component_manifest missing component rows: {', '.join(missing_component_manifest_rows)}")
    return {
        "valid": not errors,
        "errors": errors,
        "component_order": component_order,
        "required_component_order": required_component_order,
        "optional_component_order": optional_component_order,
        "components_by_id": components_by_id,
    }


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
        "runtime_component_manifest",
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
    manifest_validation = _validate_runtime_component_manifest(candidate.get("runtime_component_manifest"))
    components_by_id: dict[str, Mapping[str, Any]] = dict(manifest_validation["components_by_id"])
    required_component_order = tuple(manifest_validation["required_component_order"])
    optional_component_order = tuple(manifest_validation["optional_component_order"])

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
            metadata = components_by_id.get(component)
            if metadata is None:
                row_errors.append(f"component_input_refs[{index}].component_id unknown: {component}")
                continue
            for field in ("feature_ref", "frozen_model_config_ref", "historical_dataset_snapshot_ref"):
                if not row.get(field):
                    row_errors.append(f"component_input_refs[{index}].{field} missing")
                elif str(row.get(field)).startswith("placeholder://"):
                    row_errors.append(f"component_input_refs[{index}].{field} must not be placeholder")
            upstream_context_refs = row.get("upstream_context_refs") or []
            if not _is_sequence(upstream_context_refs):
                row_errors.append(f"component_input_refs[{index}].upstream_context_refs must be a list")
            else:
                for ref in upstream_context_refs:
                    if str(ref).startswith("placeholder://"):
                        row_errors.append(f"component_input_refs[{index}].upstream_context_refs must not contain placeholder refs")
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
            for forbidden in ("called_model_layers", "event_risk_control_policy"):
                if forbidden in row:
                    row_errors.append(f"component_input_refs[{index}].{forbidden} forbidden")

    missing_components = sorted(set(required_component_order) - set(rows_by_component))
    missing_optional_components = sorted(set(optional_component_order) - set(rows_by_component))
    valid = (
        not missing_fields
        and contract_type_valid
        and decision_time_valid
        and dataset_role_valid
        and not forbidden_actions_present
        and manifest_validation["valid"]
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
        "runtime_component_manifest_valid": manifest_validation["valid"],
        "runtime_component_manifest_errors": manifest_validation["errors"],
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
    manifest = snapshot.get("runtime_component_manifest") or {}
    manifest_validation = _validate_runtime_component_manifest(manifest)
    components_by_id: dict[str, Mapping[str, Any]] = dict(manifest_validation["components_by_id"])
    component_order = tuple(manifest_validation["component_order"]) or RUNTIME_COMPONENT_ORDER
    required_component_order = tuple(manifest_validation["required_component_order"]) or REQUIRED_RUNTIME_COMPONENT_ORDER
    routes: list[RealtimeDecisionComponentRoute] = []
    for component in component_order:
        row = rows_by_component.get(component)
        if not row:
            continue
        if component not in components_by_id:
            continue
        metadata = components_by_id[component]
        model_surfaces = tuple(metadata["required_model_surfaces"]) + tuple(metadata["optional_model_surfaces"])
        invocation_policy_field = "replay_invocation_policy" if mode == "fixture_replay" else "live_invocation_policy"
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
                invocation_policy=str(metadata.get(invocation_policy_field) or metadata.get("live_invocation_policy") or ""),
                generation_mode=mode,
                route_status="ready_for_fixture_shadow_generation" if validation["valid"] else "blocked_input_validation_failed",
            )
        )

    routed_components = {route.component_id for route in routes}
    ready = validation["valid"] and set(required_component_order).issubset(routed_components)
    return {
        "contract_type": "model_realtime_decision_route_plan",
        "route_plan_id": route_plan_id,
        "decision_input_snapshot_id": snapshot.get("decision_input_snapshot_id"),
        "decision_time": snapshot.get("decision_time"),
        "instrument_ref": snapshot.get("instrument_ref"),
        "handoff_mode": mode,
        "execution_unit": "runtime_component",
        "runtime_component_manifest": manifest,
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
        "runtime_component_manifest",
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
    manifest_validation = _validate_runtime_component_manifest(candidate.get("runtime_component_manifest"))
    components_by_id: dict[str, Mapping[str, Any]] = dict(manifest_validation["components_by_id"])
    required_component_order = tuple(manifest_validation["required_component_order"])
    optional_component_order = tuple(manifest_validation["optional_component_order"])
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
            metadata = components_by_id.get(component)
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
    missing_components = sorted(set(required_component_order) - component_set)
    missing_optional_components = sorted(set(optional_component_order) - component_set)
    valid = (
        not missing_fields
        and contract_type_valid
        and handoff_mode_valid
        and execution_unit_valid
        and input_valid
        and manifest_validation["valid"]
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
        "runtime_component_manifest_valid": manifest_validation["valid"],
        "runtime_component_manifest_errors": manifest_validation["errors"],
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

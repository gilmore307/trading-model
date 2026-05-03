"""Helpers for model configuration and promotion lifecycle rows."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

CONFIG_VERSION_TABLE = "model_config_version"
PROMOTION_CANDIDATE_TABLE = "model_promotion_candidate"
PROMOTION_DECISION_TABLE = "model_promotion_decision"
PROMOTION_ACTIVATION_TABLE = "model_promotion_activation"
PROMOTION_ROLLBACK_TABLE = "model_promotion_rollback"

_ALLOWED_DECISION_TYPES = {"approve", "reject", "defer"}
_ALLOWED_DECISION_STATUSES = {"accepted", "rejected", "deferred"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _require_non_empty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} is required")


def build_config_version_row(
    *,
    model_id: str,
    config_hash: str,
    model_version: str | None = None,
    config_status: str = "proposed",
    config_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic ``model_config_version`` row."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("config_hash", config_hash)
    payload = dict(config_payload or {})
    identity = {"model_id": model_id, "config_hash": config_hash}
    return {
        "config_version_id": _stable_id("mcfg", identity),
        "model_id": model_id,
        "model_version": model_version,
        "config_hash": config_hash,
        "config_status": config_status,
        "config_payload_json": payload,
        "status_detail": status_detail,
    }


def build_promotion_candidate_row(
    *,
    model_id: str,
    config_version_id: str,
    eval_run_id: str,
    candidate_status: str = "proposed",
    proposed_by: str | None = None,
    candidate_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic promotion candidate row backed by an eval run."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("config_version_id", config_version_id)
    _require_non_empty("eval_run_id", eval_run_id)
    payload = dict(candidate_payload or {})
    identity = {"model_id": model_id, "config_version_id": config_version_id, "eval_run_id": eval_run_id}
    return {
        "promotion_candidate_id": _stable_id("mpcand", identity),
        "model_id": model_id,
        "config_version_id": config_version_id,
        "eval_run_id": eval_run_id,
        "candidate_status": candidate_status,
        "proposed_by": proposed_by,
        "candidate_payload_json": payload,
        "status_detail": status_detail,
    }


def build_promotion_decision_row(
    *,
    promotion_candidate_id: str,
    decision_type: str,
    decision_status: str,
    decided_by: str | None = None,
    decision_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic promotion decision row."""
    _require_non_empty("promotion_candidate_id", promotion_candidate_id)
    if decision_type not in _ALLOWED_DECISION_TYPES:
        raise ValueError(f"unsupported decision_type: {decision_type!r}")
    if decision_status not in _ALLOWED_DECISION_STATUSES:
        raise ValueError(f"unsupported decision_status: {decision_status!r}")
    payload = dict(decision_payload or {})
    identity = {
        "promotion_candidate_id": promotion_candidate_id,
        "decision_type": decision_type,
        "decision_status": decision_status,
        "decision_payload": payload,
    }
    return {
        "promotion_decision_id": _stable_id("mpdec", identity),
        "promotion_candidate_id": promotion_candidate_id,
        "decision_type": decision_type,
        "decision_status": decision_status,
        "decided_by": decided_by,
        "decision_payload_json": payload,
        "status_detail": status_detail,
    }


def build_promotion_activation_row(
    *,
    model_id: str,
    to_config_version_id: str,
    promotion_decision_id: str,
    from_config_version_id: str | None = None,
    activated_by: str | None = None,
    activation_status: str = "activated",
    activation_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic model replacement/activation event row."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("to_config_version_id", to_config_version_id)
    _require_non_empty("promotion_decision_id", promotion_decision_id)
    payload = dict(activation_payload or {})
    identity = {
        "model_id": model_id,
        "from_config_version_id": from_config_version_id,
        "to_config_version_id": to_config_version_id,
        "promotion_decision_id": promotion_decision_id,
    }
    return {
        "activation_id": _stable_id("mpact", identity),
        "model_id": model_id,
        "from_config_version_id": from_config_version_id,
        "to_config_version_id": to_config_version_id,
        "promotion_decision_id": promotion_decision_id,
        "activated_by": activated_by,
        "activation_status": activation_status,
        "activation_payload_json": payload,
        "status_detail": status_detail,
    }


def build_promotion_rollback_row(
    *,
    model_id: str,
    from_config_version_id: str,
    to_config_version_id: str | None = None,
    promotion_decision_id: str | None = None,
    rollback_status: str = "requested",
    requested_by: str | None = None,
    rollback_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic rollback request row."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("from_config_version_id", from_config_version_id)
    payload = dict(rollback_payload or {})
    identity = {
        "model_id": model_id,
        "from_config_version_id": from_config_version_id,
        "to_config_version_id": to_config_version_id,
        "promotion_decision_id": promotion_decision_id,
        "rollback_payload": payload,
    }
    return {
        "rollback_id": _stable_id("mproll", identity),
        "model_id": model_id,
        "from_config_version_id": from_config_version_id,
        "to_config_version_id": to_config_version_id,
        "promotion_decision_id": promotion_decision_id,
        "rollback_status": rollback_status,
        "requested_by": requested_by,
        "rollback_payload_json": payload,
        "status_detail": status_detail,
    }

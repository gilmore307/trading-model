"""Model-side promotion evidence artifact helpers.

`trading-model` may assemble evaluation-backed evidence packages and reviewer
outputs. It must not own durable promotion decision, activation, rollback, or
manager-control-plane SQL rows; those belong in `trading-manager`.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _require_non_empty(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} is required")


def build_model_config_ref(
    *,
    model_id: str,
    config_hash: str,
    model_version: str | None = None,
    config_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic model-side config reference for evidence payloads."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("config_hash", config_hash)
    identity = {"model_id": model_id, "config_hash": config_hash}
    return {
        "config_ref_id": _stable_id("mcfgref", identity),
        "model_id": model_id,
        "model_version": model_version,
        "config_hash": config_hash,
        "config_payload": dict(config_payload or {}),
        "status_detail": status_detail,
    }


def build_promotion_candidate_evidence(
    *,
    model_id: str,
    config_ref_id: str,
    eval_run_id: str,
    proposed_by: str | None = None,
    candidate_payload: Mapping[str, Any] | None = None,
    status_detail: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic model-side promotion candidate evidence artifact."""
    _require_non_empty("model_id", model_id)
    _require_non_empty("config_ref_id", config_ref_id)
    _require_non_empty("eval_run_id", eval_run_id)
    payload = dict(candidate_payload or {})
    identity = {"model_id": model_id, "config_ref_id": config_ref_id, "eval_run_id": eval_run_id}
    return {
        "candidate_ref": _stable_id("mpcandref", identity),
        "model_id": model_id,
        "config_ref_id": config_ref_id,
        "eval_run_id": eval_run_id,
        "proposed_by": proposed_by,
        "candidate_payload": payload,
        "status_detail": status_detail,
    }


def build_review_artifact_from_review(
    *,
    candidate_ref: str,
    review: Mapping[str, Any],
    reviewed_by: str = "agent_promotion_reviewer",
) -> dict[str, Any]:
    """Build a model-side review artifact without implying durable approval."""
    _require_non_empty("candidate_ref", candidate_ref)
    from .agent_review import validate_promotion_review

    normalized = validate_promotion_review(review)
    identity = {
        "candidate_ref": candidate_ref,
        "decision_type": normalized["decision_type"],
        "decision_status": normalized["decision_status"],
        "review": normalized,
    }
    return {
        "review_artifact_id": _stable_id("mpreview", identity),
        "candidate_ref": candidate_ref,
        "reviewed_by": reviewed_by,
        "can_promote": normalized["can_promote"],
        "decision_type": normalized["decision_type"],
        "decision_status": normalized["decision_status"],
        "review_payload": normalized,
        "status_detail": "; ".join(normalized["blockers"] or normalized["reasons"]),
        "manager_control_plane_required": True,
    }

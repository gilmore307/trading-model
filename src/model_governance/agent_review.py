"""Agent-backed promotion review helpers.

The functions in this module prepare evidence for a reviewer agent and validate
that the agent returns a constrained promotion decision. They do not promote a
model and do not write to PostgreSQL.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .promotion import build_promotion_decision_row

ALLOWED_DECISION_TYPES = {"approve", "reject", "defer"}
ALLOWED_DECISION_STATUSES = {"accepted", "rejected", "deferred"}


def build_market_regime_promotion_prompt(
    *,
    evaluation_summary: Mapping[str, Any],
    config_version_row: Mapping[str, Any],
    promotion_candidate_row: Mapping[str, Any],
) -> str:
    """Build the reviewer-agent prompt for a MarketRegimeModel promotion gate."""
    evidence = {
        "evaluation_summary": dict(evaluation_summary),
        "config_version": dict(config_version_row),
        "promotion_candidate": dict(promotion_candidate_row),
    }
    return (
        "You are the independent promotion reviewer for trading-model MarketRegimeModel.\n"
        "Evaluate whether this candidate can be promoted. Be strict.\n\n"
        "Hard rules:\n"
        "- Return ONLY one JSON object. No markdown, no prose outside JSON.\n"
        "- Do not approve if evidence is fixture-only, dry-run-only, missing real-data metrics, "
        "or missing explicit thresholds.\n"
        "- Promotion requires an evaluation-backed candidate, sufficient metric coverage, "
        "explicit acceptance thresholds, and no unresolved data-leakage or cleanup blocker.\n"
        "- If evidence is insufficient, use decision_type='defer' and decision_status='deferred'.\n"
        "- A review decision is not an active production pointer.\n\n"
        "Required JSON schema:\n"
        "{\n"
        "  \"can_promote\": boolean,\n"
        "  \"decision_type\": \"approve\" | \"reject\" | \"defer\",\n"
        "  \"decision_status\": \"accepted\" | \"rejected\" | \"deferred\",\n"
        "  \"confidence\": number,\n"
        "  \"reasons\": [string],\n"
        "  \"blockers\": [string],\n"
        "  \"required_next_steps\": [string],\n"
        "  \"evidence_checks\": { string: boolean }\n"
        "}\n\n"
        "Evidence:\n"
        f"{json.dumps(evidence, indent=2, sort_keys=True, default=str)}\n"
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a single JSON object from agent output."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("agent output is empty")
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("agent output did not contain a JSON object") from None
        parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("agent output JSON must be an object")
    return parsed


def validate_promotion_review(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize an agent promotion review payload."""
    required = [
        "can_promote",
        "decision_type",
        "decision_status",
        "confidence",
        "reasons",
        "blockers",
        "required_next_steps",
        "evidence_checks",
    ]
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"promotion review missing required fields: {missing}")

    can_promote = payload["can_promote"]
    if not isinstance(can_promote, bool):
        raise ValueError("can_promote must be boolean")
    decision_type = str(payload["decision_type"])
    decision_status = str(payload["decision_status"])
    if decision_type not in ALLOWED_DECISION_TYPES:
        raise ValueError(f"unsupported decision_type: {decision_type!r}")
    if decision_status not in ALLOWED_DECISION_STATUSES:
        raise ValueError(f"unsupported decision_status: {decision_status!r}")
    if can_promote and (decision_type != "approve" or decision_status != "accepted"):
        raise ValueError("can_promote=true requires approve/accepted")
    if not can_promote and decision_type == "approve":
        raise ValueError("approve decision requires can_promote=true")

    confidence = float(payload["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be in [0, 1]")

    reasons = _string_list(payload["reasons"], "reasons")
    blockers = _string_list(payload["blockers"], "blockers")
    next_steps = _string_list(payload["required_next_steps"], "required_next_steps")
    evidence_checks = payload["evidence_checks"]
    if not isinstance(evidence_checks, Mapping) or not all(isinstance(key, str) and isinstance(value, bool) for key, value in evidence_checks.items()):
        raise ValueError("evidence_checks must be an object of boolean values")

    return {
        "can_promote": can_promote,
        "decision_type": decision_type,
        "decision_status": decision_status,
        "confidence": confidence,
        "reasons": reasons,
        "blockers": blockers,
        "required_next_steps": next_steps,
        "evidence_checks": dict(evidence_checks),
    }


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be a list of strings")
    output = [str(item) for item in value]
    if any(not item.strip() for item in output):
        raise ValueError(f"{field} must not contain blank strings")
    return output


def build_decision_row_from_review(
    *,
    promotion_candidate_id: str,
    review: Mapping[str, Any],
    decided_by: str = "agent_promotion_reviewer",
) -> dict[str, Any]:
    """Convert a validated review payload into a promotion decision row."""
    normalized = validate_promotion_review(review)
    return build_promotion_decision_row(
        promotion_candidate_id=promotion_candidate_id,
        decision_type=normalized["decision_type"],
        decision_status=normalized["decision_status"],
        decided_by=decided_by,
        decision_payload=normalized,
        status_detail="; ".join(normalized["blockers"] or normalized["reasons"]),
    )

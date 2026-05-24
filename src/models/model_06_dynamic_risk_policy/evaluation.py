"""Offline evaluation helpers for Layer 6 dynamic risk-policy rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_premium_efficiency_1W",
    "realized_risk_budget_efficiency_1W",
    "realized_drawdown_pressure_1W",
    "realized_policy_breach_1W",
    "realized_exposure_capacity_used_1W",
}


def build_dynamic_risk_policy_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future risk-policy outcomes by dynamic_risk_policy_state_ref."""

    outcomes = {str(row.get("dynamic_risk_policy_state_ref")): row for row in outcome_rows if row.get("dynamic_risk_policy_state_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("dynamic_risk_policy_state_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {
            "dynamic_risk_policy_state_ref": ref,
            "policy_scope": model_row.get("policy_scope"),
            "policy_scope_id": model_row.get("policy_scope_id"),
            "target_candidate_id": model_row.get("target_candidate_id"),
        }
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"Layer 6 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

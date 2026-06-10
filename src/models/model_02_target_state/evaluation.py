"""Offline evaluation helpers for M02 target-state rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "future_target_return_1W",
    "future_target_path_stability_1W",
    "future_target_liquidity_1W",
    "target_state_realized_utility_1W",
}


def build_target_state_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcomes = {str(row.get("target_context_state_ref")): row for row in outcome_rows if row.get("target_context_state_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("target_context_state_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"target_context_state_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"M02 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

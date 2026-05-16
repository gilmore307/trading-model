"""Offline evaluation helpers for Layer 6 position projection rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_position_utility_5min",
    "realized_position_utility_15min",
    "realized_position_utility_60min",
    "realized_position_utility_390min",
    "realized_target_exposure_utility_390min",
    "realized_position_gap_utility_390min",
    "realized_cost_to_adjust_position_390min",
    "realized_risk_budget_breach_390min",
    "current_position_hold_utility_390min",
    "flat_position_utility_390min",
    "candidate_exposure_utility_curve_390min",
}


def build_position_projection_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future position-utility outcomes by ``position_projection_vector_ref``."""

    outcomes = {str(row.get("position_projection_vector_ref")): row for row in outcome_rows if row.get("position_projection_vector_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("position_projection_vector_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"position_projection_vector_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
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

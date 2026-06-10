"""Evaluation helpers for M04 UnifiedDecisionModel.

Evaluation labels are joined offline by ``unified_decision_vector_ref``. Runtime
M04 rows must not contain realized outcomes, fills, or future returns.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORBIDDEN_LABEL_FIELDS = {
    "future_return",
    "future_fill",
    "realized_pnl",
    "realized_underlying_return",
    "realized_decision_utility",
    "realized_max_drawdown",
    "target_hit_time",
    "stop_hit_time",
}


def build_unified_decision_labels(model_rows: Sequence[Mapping[str, Any]], outcome_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future decision outcomes by ``unified_decision_vector_ref``."""

    outcomes = {str(row.get("unified_decision_vector_ref")): row for row in outcome_rows if row.get("unified_decision_vector_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("unified_decision_vector_ref") or "")
        outcome = outcomes.get(ref)
        if not outcome:
            continue
        label = {
            "unified_decision_vector_ref": ref,
            "target_candidate_id": model_row.get("target_candidate_id"),
        }
        for key, value in outcome.items():
            if key == "unified_decision_vector_ref":
                continue
            label[str(key)] = value
        labels.append(label)
    return labels


def assert_no_label_leakage(row: Mapping[str, Any]) -> None:
    """Raise when runtime rows contain offline outcome fields."""

    _assert_no_label_leakage(row)


def _assert_no_label_leakage(value: Any, path: str = "row") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_LABEL_FIELDS:
                raise ValueError(f"runtime row contains offline label field {path}.{key}")
            _assert_no_label_leakage(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_label_leakage(nested, f"{path}[{index}]")

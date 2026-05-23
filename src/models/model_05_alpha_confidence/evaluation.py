"""Offline evaluation helpers for Layer 5 alpha confidence rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "forward_return_10min",
    "forward_return_1h",
    "forward_return_1D",
    "forward_return_1W",
    "market_adjusted_forward_return_1W",
    "sector_adjusted_forward_return_1W",
    "idiosyncratic_residual_return_1W",
    "realized_max_favorable_excursion_1W",
    "realized_max_adverse_excursion_1W",
    "alpha_tradable_label_1W",
}


def build_alpha_confidence_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future alpha outcomes by ``alpha_confidence_vector_ref`` for evaluation."""

    outcomes = {str(row.get("alpha_confidence_vector_ref")): row for row in outcome_rows if row.get("alpha_confidence_vector_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("alpha_confidence_vector_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"alpha_confidence_vector_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"Layer 5 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

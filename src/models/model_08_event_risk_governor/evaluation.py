"""Offline evaluation helpers for Layer 8 event-risk rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_symbol_move_after_event_5min",
    "realized_symbol_move_after_event_15min",
    "realized_symbol_move_after_event_60min",
    "realized_symbol_move_after_event_390min",
    "post_event_gap_realization_390min",
    "post_event_reversal_realization_390min",
    "post_event_liquidity_degradation_390min",
}


def build_event_risk_governor_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future outcomes to event-context rows for offline evaluation only.

    The join key is ``event_context_vector_ref``. Returned labels are deliberately
    separate from inference rows so realized future outcomes cannot leak into
    ``event_context_vector``.
    """

    outcomes = {str(row.get("event_context_vector_ref")): row for row in outcome_rows if row.get("event_context_vector_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("event_context_vector_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"event_context_vector_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    """Raise if offline label fields appear in an inference row."""

    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"Layer 8 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

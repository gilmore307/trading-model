"""Offline evaluation helpers for Layer 4 event-failure-risk rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_strategy_failure_5min",
    "realized_strategy_failure_15min",
    "realized_strategy_failure_60min",
    "realized_strategy_failure_390min",
    "realized_entry_block_benefit_390min",
    "realized_exposure_cap_benefit_390min",
    "realized_strategy_disable_benefit_390min",
    "realized_path_risk_amplification_390min",
}


def build_event_failure_risk_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future event-failure outcomes by ``event_failure_risk_vector_ref`` for evaluation."""

    outcomes = {str(row.get("event_failure_risk_vector_ref")): row for row in outcome_rows if row.get("event_failure_risk_vector_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("event_failure_risk_vector_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"event_failure_risk_vector_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"Layer 4 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

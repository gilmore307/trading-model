"""Offline evaluation helpers for M06 residual event governance rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_residual_event_loss_1W",
    "realized_intervention_utility_1W",
    "missed_event_failure_label_1W",
    "false_block_label_1W",
    "post_event_gap_realization_1W",
    "post_event_reversal_realization_1W",
    "post_event_liquidity_degradation_1W",
}


def build_residual_event_governance_labels(
    model_rows: Iterable[Mapping[str, Any]],
    outcome_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Join future outcomes to M06 rows for offline evaluation only."""

    outcomes = {
        str(row.get("event_risk_intervention_ref")): row
        for row in outcome_rows
        if row.get("event_risk_intervention_ref")
    }
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("event_risk_intervention_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"event_risk_intervention_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    """Raise if offline label fields appear in an inference row."""

    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"M06 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

"""Offline evaluation helpers for M01 background-context rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "future_market_volatility_1W",
    "future_market_liquidity_degradation_1W",
    "future_sector_dispersion_1W",
    "background_context_realized_utility_1W",
}


def build_background_context_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcomes = {str(row.get("background_context_state_ref")): row for row in outcome_rows if row.get("background_context_state_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("background_context_state_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"background_context_state_ref": ref}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"M01 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

"""Offline evaluation helpers for M05 option-expression rows."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

LABEL_FIELDS = {
    "realized_option_return_10min",
    "realized_option_return_1h",
    "realized_option_return_1D",
    "realized_option_return_1W",
    "realized_option_max_favorable_excursion_1W",
    "realized_option_max_adverse_excursion_1W",
    "target_premium_hit_before_stop_label_1W",
    "premium_stop_hit_before_target_label_1W",
    "option_spread_adjusted_return_1W",
    "selected_contract_regret_vs_best_candidate_1W",
    "realized_option_mid_return_1W",
    "realized_option_bid_exit_return_1W",
    "realized_option_spread_cost_1W",
    "realized_iv_change_1W",
    "realized_theta_decay_1W",
    "realized_delta_path_exposure_1W",
    "underlying_target_hit_but_option_lost_label_1W",
    "option_no_expression_opportunity_cost_1W",
    "option_expression_avoided_loss_value_1W",
    "candidate_contract_utility_curve_1W",
}


def build_option_expression_labels(model_rows: Iterable[Mapping[str, Any]], outcome_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Join future option-expression outcomes for offline evaluation only."""

    outcomes = {str(row.get("option_expression_plan_ref")): row for row in outcome_rows if row.get("option_expression_plan_ref")}
    labels: list[dict[str, Any]] = []
    for model_row in model_rows:
        ref = str(model_row.get("option_expression_plan_ref") or "")
        if not ref or ref not in outcomes:
            continue
        outcome = outcomes[ref]
        label = {"option_expression_plan_ref": ref, "target_candidate_id": model_row.get("target_candidate_id")}
        for field in LABEL_FIELDS:
            if field in outcome:
                label[field] = outcome[field]
        labels.append(label)
    return labels


def assert_no_label_leakage(model_row: Mapping[str, Any]) -> None:
    leaked = sorted(field for field in LABEL_FIELDS if _contains_key(model_row, field))
    if leaked:
        raise ValueError(f"M05 label fields leaked into inference row: {', '.join(leaked)}")


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(nested, key) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_key(nested, key) for nested in value)
    return False

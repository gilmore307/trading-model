"""Contract constants for M04 UnifiedDecisionModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M04"
MODEL_ID: Final[str] = "unified_decision_model"
MODEL_SURFACE: Final[str] = "model_04_unified_decision"
CONCEPTUAL_OUTPUT: Final[str] = "unified_decision_vector"
MODEL_VERSION: Final[str] = "unified_decision_vector_contract"
VECTOR_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "4_edge_direction_score_<horizon>",
    "4_after_cost_edge_score_<horizon>",
    "4_expected_return_score_<horizon>",
    "4_edge_confidence_score_<horizon>",
    "4_downside_risk_score_<horizon>",
    "4_risk_budget_score_<horizon>",
    "4_new_exposure_permission_score_<horizon>",
    "4_target_exposure_score_<horizon>",
    "4_target_allocation_fraction_<horizon>",
    "4_position_gap_score_<horizon>",
    "4_trade_intensity_score_<horizon>",
    "4_materiality_adjusted_action_score_<horizon>",
    "4_no_trade_probability_score_<horizon>",
    "4_action_eligibility_score_<horizon>",
    "4_action_direction_score_<horizon>",
    "4_entry_quality_score_<horizon>",
    "4_action_confidence_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "4_resolved_decision_horizon",
    "4_resolved_underlying_action_type",
    "4_resolved_action_side",
    "4_resolved_target_exposure_score",
    "4_resolved_target_allocation_fraction",
    "4_resolved_position_gap_score",
    "4_resolved_trade_intensity_score",
    "4_resolved_materiality_adjusted_action_score",
    "4_resolved_no_trade_probability_score",
    "4_resolved_action_confidence_score",
    "4_resolved_reason_codes",
)

PLANNED_ACTION_TYPES: Final[tuple[str, ...]] = (
    "open_long",
    "reduce_long",
    "close_long",
    "open_short",
    "reduce_short",
    "cover_short",
    "maintain",
    "no_trade",
    "bearish_underlying_path_but_no_short_allowed",
)

ENTRY_STYLES: Final[tuple[str, ...]] = (
    "limit_near_mid",
    "limit_or_pullback",
    "wait_for_pullback",
    "wait_for_breakout_confirmation",
    "maintain_existing_entry",
    "no_entry",
)

HORIZON_MINUTES: Final[dict[str, int]] = {
    "10min": 10,
    "1h": 60,
    "1D": 24 * 60,
    "1W": 7 * 24 * 60,
}

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "alpha_confidence_vector",
        "dynamic_risk_policy_state",
        "position_projection_vector",
        "underlying_action_vector",
        "underlying_action_plan",
        "order_type",
        "route",
        "time_in_force",
        "send_order",
        "replace_order",
        "cancel_order",
        "broker_order_id",
        "broker_account_id",
        "execution_instruction",
        "order_instruction",
        "final_action",
        "option_symbol",
        "option_right",
        "strike",
        "expiration",
        "dte",
        "delta",
        "gamma",
        "theta",
        "vega",
        "specific_contract_ref",
        "option_contract_ref",
        "future_return",
        "future_fill",
        "realized_pnl",
    }
)

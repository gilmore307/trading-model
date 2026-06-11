"""Contract constants for M05 OptionExpressionModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M05"
MODEL_ID: Final[str] = "option_expression_model"
MODEL_SURFACE: Final[str] = "model_05_option_expression"
CONCEPTUAL_OUTPUT: Final[str] = "option_expression_plan"
MODEL_VERSION: Final[str] = "option_expression_plan_contract"
PRIMARY_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
VECTOR_OUTPUT: Final[str] = "expression_vector"
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "5_option_expression_eligibility_score_<horizon>",
    "5_option_expression_direction_score_<horizon>",
    "5_option_contract_fit_score_<horizon>",
    "5_option_liquidity_fit_score_<horizon>",
    "5_option_iv_fit_score_<horizon>",
    "5_option_greek_fit_score_<horizon>",
    "5_option_reward_risk_score_<horizon>",
    "5_option_theta_risk_score_<horizon>",
    "5_option_fill_quality_score_<horizon>",
    "5_option_expression_confidence_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "5_resolved_expression_type",
    "5_resolved_option_right",
    "5_resolved_option_surface_status",
    "5_resolved_dominant_horizon",
    "5_resolved_selected_contract_ref",
    "5_resolved_contract_fit_score",
    "5_resolved_expression_confidence_score",
    "5_resolved_no_option_reason_codes",
    "5_resolved_reason_codes",
)

EXPRESSION_TYPES: Final[tuple[str, ...]] = (
    "long_call",
    "long_put",
    "underlying_only_expression",
    "no_option_expression",
)

OPTION_RIGHTS: Final[tuple[str, ...]] = ("call", "put", "none")

OPTION_SURFACE_STATUSES: Final[tuple[str, ...]] = (
    "optionable_chain_available",
    "optionable_chain_missing",
    "non_optionable_underlying",
)

EVENT_STATE_CONSUMED_FIELDS: Final[tuple[str, ...]] = (
    "3_event_option_price_impact_score_<horizon>",
    "3_event_volatility_surface_impact_score_<horizon>",
    "3_event_option_liquidity_spread_impact_score_<horizon>",
    "3_event_expiry_gamma_flow_impact_score_<horizon>",
)

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "underlying_action_plan",
        "underlying_action_vector",
        "underlying_action_plan_ref",
        "order_type",
        "route",
        "routing_destination",
        "time_in_force",
        "send_order",
        "replace_order",
        "cancel_order",
        "broker_order_id",
        "broker_account_id",
        "execution_instruction",
        "order_instruction",
        "final_action",
        "final_order_quantity",
        "order_quantity",
    }
)

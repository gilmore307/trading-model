"""Physical constants for Layer 9 OptionExpressionModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "option_expression_model"
MODEL_LAYER: Final[str] = "layer_09_option_expression"  # current conceptual layer token
MODEL_SURFACE: Final[str] = "model_09_option_expression"
MODEL_VERSION: Final[str] = "option_expression_plan_contract"
PRIMARY_OUTPUT: Final[str] = "option_expression_plan"
VECTOR_OUTPUT: Final[str] = "expression_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "9_option_expression_eligibility_score_<horizon>",
    "9_option_expression_direction_score_<horizon>",
    "9_option_contract_fit_score_<horizon>",
    "9_option_liquidity_fit_score_<horizon>",
    "9_option_iv_fit_score_<horizon>",
    "9_option_greek_fit_score_<horizon>",
    "9_option_reward_risk_score_<horizon>",
    "9_option_theta_risk_score_<horizon>",
    "9_option_fill_quality_score_<horizon>",
    "9_option_expression_confidence_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "9_resolved_expression_type",
    "9_resolved_option_right",
    "9_resolved_dominant_horizon",
    "9_resolved_selected_contract_ref",
    "9_resolved_contract_fit_score",
    "9_resolved_expression_confidence_score",
    "9_resolved_no_option_reason_codes",
    "9_resolved_reason_codes",
)

EXPRESSION_TYPES: Final[tuple[str, ...]] = (
    "long_call",
    "long_put",
    "underlying_only_expression",
    "no_option_expression",
)

OPTION_RIGHTS: Final[tuple[str, ...]] = ("call", "put", "none")

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
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

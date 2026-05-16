"""Legacy physical constants for conceptual Layer 7 OptionExpressionModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "option_expression_model"
MODEL_LAYER: Final[str] = "layer_08_option_expression"  # legacy physical layer token until a dedicated migration
MODEL_SURFACE: Final[str] = "model_08_option_expression"
MODEL_VERSION: Final[str] = "option_expression_plan_contract"
PRIMARY_OUTPUT: Final[str] = "option_expression_plan"
VECTOR_OUTPUT: Final[str] = "expression_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "8_option_expression_eligibility_score_<horizon>",
    "8_option_expression_direction_score_<horizon>",
    "8_option_contract_fit_score_<horizon>",
    "8_option_liquidity_fit_score_<horizon>",
    "8_option_iv_fit_score_<horizon>",
    "8_option_greek_fit_score_<horizon>",
    "8_option_reward_risk_score_<horizon>",
    "8_option_theta_risk_score_<horizon>",
    "8_option_fill_quality_score_<horizon>",
    "8_option_expression_confidence_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "8_resolved_expression_type",
    "8_resolved_option_right",
    "8_resolved_dominant_horizon",
    "8_resolved_selected_contract_ref",
    "8_resolved_contract_fit_score",
    "8_resolved_expression_confidence_score",
    "8_resolved_no_option_reason_codes",
    "8_resolved_reason_codes",
)

EXPRESSION_TYPES: Final[tuple[str, ...]] = (
    "long_call",
    "long_put",
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

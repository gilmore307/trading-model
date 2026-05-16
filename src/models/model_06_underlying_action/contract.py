"""Current physical constants for Layer 6 UnderlyingActionModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "underlying_action_model"
MODEL_LAYER: Final[str] = "layer_06_underlying_action"  # current conceptual layer token
MODEL_SURFACE: Final[str] = "model_06_underlying_action"
MODEL_VERSION: Final[str] = "underlying_action_plan_contract"
PRIMARY_OUTPUT: Final[str] = "underlying_action_plan"
VECTOR_OUTPUT: Final[str] = "underlying_action_vector"

HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "6_underlying_trade_eligibility_score_<horizon>",
    "6_underlying_action_direction_score_<horizon>",
    "6_underlying_trade_intensity_score_<horizon>",
    "6_underlying_entry_quality_score_<horizon>",
    "6_underlying_expected_return_score_<horizon>",
    "6_underlying_adverse_risk_score_<horizon>",
    "6_underlying_reward_risk_score_<horizon>",
    "6_underlying_liquidity_fit_score_<horizon>",
    "6_underlying_holding_time_fit_score_<horizon>",
    "6_underlying_action_confidence_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "6_resolved_underlying_action_type",
    "6_resolved_action_side",
    "6_resolved_dominant_horizon",
    "6_resolved_trade_eligibility_score",
    "6_resolved_trade_intensity_score",
    "6_resolved_entry_quality_score",
    "6_resolved_action_confidence_score",
    "6_resolved_reason_codes",
)

PLANNED_ACTION_TYPES: Final[tuple[str, ...]] = (
    "open_long",
    "increase_long",
    "reduce_long",
    "close_long",
    "open_short",
    "increase_short",
    "reduce_short",
    "cover_short",
    "maintain",
    "no_trade",
    "bearish_underlying_path_but_no_short_allowed",
)

ENTRY_STYLES: Final[tuple[str, ...]] = (
    "marketable_review",
    "limit_near_mid",
    "limit_or_pullback",
    "wait_for_pullback",
    "wait_for_breakout_confirmation",
    "maintain_existing_entry",
    "no_entry",
)

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
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
    }
)

HORIZON_MINUTES: Final[dict[str, int]] = {
    "5min": 5,
    "15min": 15,
    "60min": 60,
    "390min": 390,
}

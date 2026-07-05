"""Contract constants for M03 EventStateModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M03"
MODEL_ID: Final[str] = "event_state_model"
MODEL_SURFACE: Final[str] = "model_03_event_state"
CONCEPTUAL_OUTPUT: Final[str] = "event_state_vector"
MODEL_VERSION: Final[str] = "event_state_vector_contract"
PRIMARY_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

EVENT_IMPACT_CHANNELS: Final[tuple[str, ...]] = (
    "underlying_price",
    "option_price",
    "volatility_surface",
    "option_liquidity_spread",
    "expiry_gamma_flow",
)

EVENT_DISTRIBUTION_EFFECT_CHANNELS: Final[tuple[str, ...]] = (
    "mean_shift",
    "mode_shift",
    "directional_contribution",
    "variance_multiplier",
    "left_tail_delta",
    "right_tail_delta",
    "skew_delta",
    "confidence_discount",
    "gate_pressure",
)

DEFAULT_ALLOWED_EFFECT_PROFILE: Final[dict[str, bool]] = {
    "can_change_mean": False,
    "can_change_mode": False,
    "can_add_directional_contribution": False,
    "can_change_variance": True,
    "can_change_left_tail": True,
    "can_change_right_tail": True,
    "can_change_skew": True,
    "can_change_confidence": True,
    "can_raise_gate": True,
}

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "3_event_response_direction_score_<horizon>",
    "3_event_response_strength_score_<horizon>",
    "3_event_uncertainty_score_<horizon>",
    "3_event_path_risk_score_<horizon>",
    "3_event_entry_block_pressure_score_<horizon>",
    "3_event_exposure_cap_pressure_score_<horizon>",
    "3_event_strategy_disable_pressure_score_<horizon>",
    "3_event_applicability_confidence_score_<horizon>",
    "3_event_underlying_price_impact_score_<horizon>",
    "3_event_option_price_impact_score_<horizon>",
    "3_event_volatility_surface_impact_score_<horizon>",
    "3_event_option_liquidity_spread_impact_score_<horizon>",
    "3_event_expiry_gamma_flow_impact_score_<horizon>",
    "3_event_mean_shift_score_<horizon>",
    "3_event_mode_shift_score_<horizon>",
    "3_event_directional_contribution_score_<horizon>",
    "3_event_variance_multiplier_score_<horizon>",
    "3_event_left_tail_delta_score_<horizon>",
    "3_event_right_tail_delta_score_<horizon>",
    "3_event_skew_delta_score_<horizon>",
    "3_event_confidence_discount_score_<horizon>",
    "3_event_gate_pressure_score_<horizon>",
)

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "standalone_event_alpha",
        "event_alpha_score",
        "event_family_parameter_update",
        "selected_impact_window_update",
        "unified_decision_vector",
        "underlying_action_plan",
        "option_expression_plan",
        "order_type",
        "broker_order_id",
        "future_return",
        "realized_pnl",
    }
)

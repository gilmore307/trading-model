"""Current physical constants for Layer 5 PositionProjectionModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "position_projection_model"
MODEL_LAYER: Final[str] = "layer_05_position_projection"  # current conceptual layer token
MODEL_SURFACE: Final[str] = "model_05_position_projection"
MODEL_VERSION: Final[str] = "position_projection_vector_contract"
VECTOR_OUTPUT: Final[str] = "position_projection_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")
SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "5_target_position_bias_score_<horizon>",
    "5_target_exposure_score_<horizon>",
    "5_current_position_alignment_score_<horizon>",
    "5_position_gap_score_<horizon>",
    "5_position_gap_magnitude_score_<horizon>",
    "5_expected_position_utility_score_<horizon>",
    "5_cost_to_adjust_position_score_<horizon>",
    "5_risk_budget_fit_score_<horizon>",
    "5_position_state_stability_score_<horizon>",
    "5_projection_confidence_score_<horizon>",
)
RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "5_dominant_projection_horizon",
    "5_horizon_conflict_state",
    "5_resolved_target_exposure_score",
    "5_resolved_position_gap_score",
    "5_projection_resolution_confidence_score",
    "5_horizon_resolution_reason_codes",
)
FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset({
    "buy", "sell", "hold", "open", "close", "reverse", "order_quantity", "order_type",
    "route", "broker_order_id", "option_contract", "option_symbol", "strike", "dte",
    "delta", "gamma", "theta", "vega", "final_action", "execution_instruction",
    "future_return", "future_fill", "realized_pnl",
})

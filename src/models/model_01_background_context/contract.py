"""Contract constants for M01 BackgroundContextModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M01"
MODEL_ID: Final[str] = "background_context_model"
MODEL_SURFACE: Final[str] = "model_01_background_context"
CONCEPTUAL_OUTPUT: Final[str] = "background_context_state"
MODEL_VERSION: Final[str] = "background_context_state_contract"
PRIMARY_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "1_market_direction_score_<horizon>",
    "1_market_trend_quality_score_<horizon>",
    "1_market_risk_stress_score_<horizon>",
    "1_market_liquidity_support_score_<horizon>",
    "1_market_volatility_pressure_score_<horizon>",
    "1_sector_breadth_score_<horizon>",
    "1_sector_dispersion_score_<horizon>",
    "1_background_context_quality_score_<horizon>",
)

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "target_candidate_id",
        "target_context_state",
        "event_state_vector",
        "unified_decision_vector",
        "option_expression_plan",
        "event_risk_intervention",
        "underlying_action_plan",
        "order_type",
        "broker_order_id",
        "future_return",
        "realized_pnl",
    }
)

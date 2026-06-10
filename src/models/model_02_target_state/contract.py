"""Contract constants for M02 TargetStateModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M02"
MODEL_ID: Final[str] = "target_state_model"
MODEL_SURFACE: Final[str] = "model_02_target_state"
CONCEPTUAL_OUTPUT: Final[str] = "target_context_state"
MODEL_VERSION: Final[str] = "target_context_state_contract"
PRIMARY_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "2_target_direction_score_<horizon>",
    "2_target_trend_quality_score_<horizon>",
    "2_target_path_stability_score_<horizon>",
    "2_target_noise_score_<horizon>",
    "2_target_transition_risk_score_<horizon>",
    "2_context_support_quality_score_<horizon>",
    "2_tradability_score_<horizon>",
)

FORBIDDEN_MODEL_FACING_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "symbol",
        "ticker",
        "company_name",
        "asset_name",
        "cusip",
        "isin",
        "figi",
        "underlying_action_plan",
        "unified_decision_vector",
        "option_expression_plan",
        "order_type",
        "broker_order_id",
        "future_return",
        "realized_pnl",
    }
)

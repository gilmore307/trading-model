"""Current physical constants for Layer 4 AlphaConfidenceModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "alpha_confidence_model"
MODEL_LAYER: Final[str] = "layer_04_alpha_confidence"  # current conceptual layer token
MODEL_SURFACE: Final[str] = "model_04_alpha_confidence"
MODEL_VERSION: Final[str] = "alpha_confidence_vector_contract"
VECTOR_OUTPUT: Final[str] = "alpha_confidence_vector"
BASE_DIAGNOSTIC_OUTPUT: Final[str] = "base_alpha_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")
SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "4_alpha_direction_score_<horizon>",
    "4_alpha_strength_score_<horizon>",
    "4_expected_return_score_<horizon>",
    "4_alpha_confidence_score_<horizon>",
    "4_signal_reliability_score_<horizon>",
    "4_path_quality_score_<horizon>",
    "4_reversal_risk_score_<horizon>",
    "4_drawdown_risk_score_<horizon>",
    "4_alpha_tradability_score_<horizon>",
)
FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset({
    "buy", "sell", "hold", "target_exposure", "position_size", "account_risk_allocation",
    "option_contract", "option_symbol", "strike", "dte", "delta", "order_type",
    "broker_order_id", "execution_result", "final_action", "current_position_size",
    "current_pnl", "future_return", "future_fill", "realized_pnl",
})

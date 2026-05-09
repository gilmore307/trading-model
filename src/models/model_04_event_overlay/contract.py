"""Layer 4 EventOverlayModel V1 contract constants."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "event_overlay_model"
MODEL_LAYER: Final[str] = "layer_04_event_overlay"
MODEL_SURFACE: Final[str] = "model_04_event_overlay"
MODEL_VERSION: Final[str] = "event_context_vector_v1_contract"
VECTOR_OUTPUT: Final[str] = "event_context_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")
HORIZON_MINUTES: Final[dict[str, int]] = {"5min": 5, "15min": 15, "60min": 60, "390min": 390}
PRICE_ACTION_EVENT_TYPES: Final[tuple[str, ...]] = (
    "false_breakout",
    "false_breakdown",
    "liquidity_sweep_high",
    "liquidity_sweep_low",
    "bull_trap",
    "bear_trap",
)
CORE_SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "4_event_presence_score_<horizon>",
    "4_event_timing_proximity_score_<horizon>",
    "4_event_intensity_score_<horizon>",
    "4_event_direction_bias_score_<horizon>",
    "4_event_context_alignment_score_<horizon>",
    "4_event_uncertainty_score_<horizon>",
    "4_event_gap_risk_score_<horizon>",
    "4_event_reversal_risk_score_<horizon>",
    "4_event_liquidity_disruption_score_<horizon>",
    "4_event_contagion_risk_score_<horizon>",
    "4_event_context_quality_score_<horizon>",
)
IMPACT_SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "4_event_market_impact_score_<horizon>",
    "4_event_sector_impact_score_<horizon>",
    "4_event_industry_impact_score_<horizon>",
    "4_event_theme_factor_impact_score_<horizon>",
    "4_event_peer_group_impact_score_<horizon>",
    "4_event_symbol_impact_score_<horizon>",
    "4_event_microstructure_impact_score_<horizon>",
    "4_event_scope_confidence_score_<horizon>",
    "4_event_scope_escalation_risk_score_<horizon>",
    "4_event_target_relevance_score_<horizon>",
)
FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset({
    "buy", "sell", "hold", "alpha_confidence", "expected_residual_return", "position_size",
    "target_exposure", "option_contract", "option_symbol", "strike", "dte", "delta",
    "order_instruction", "order_type", "broker_order_id", "final_action", "current_pnl",
    "future_return", "future_price", "realized_pnl",
})

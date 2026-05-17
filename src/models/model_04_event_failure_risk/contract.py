"""Current physical constants for Layer 4 EventFailureRiskModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "event_failure_risk_model"
MODEL_LAYER: Final[str] = "layer_04_event_failure_risk"
MODEL_SURFACE: Final[str] = "model_04_event_failure_risk"
MODEL_VERSION: Final[str] = "event_failure_risk_vector_contract"
VECTOR_OUTPUT: Final[str] = "event_failure_risk_vector"
HORIZONS: Final[tuple[str, ...]] = ("5min", "15min", "60min", "390min")
SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "4_event_strategy_failure_risk_score_<horizon>",
    "4_event_entry_block_pressure_score_<horizon>",
    "4_event_exposure_cap_pressure_score_<horizon>",
    "4_event_strategy_disable_pressure_score_<horizon>",
    "4_event_path_risk_amplifier_score_<horizon>",
    "4_event_evidence_quality_score_<horizon>",
    "4_event_applicability_confidence_score_<horizon>",
)
RESOLVED_STATUSES: Final[tuple[str, ...]] = (
    "no_reviewed_event_failure_risk",
    "observe_only",
    "alpha_conditioning_required",
    "entry_block_recommended",
    "exposure_cap_recommended",
    "strategy_family_disable_recommended",
    "human_review_required",
)
FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset({
    "buy", "sell", "hold", "target_exposure", "position_size", "account_risk_allocation",
    "option_contract", "option_symbol", "strike", "dte", "delta", "order_type",
    "broker_order_id", "execution_result", "final_action", "current_position_size",
    "current_pnl", "future_return", "future_fill", "realized_pnl",
})

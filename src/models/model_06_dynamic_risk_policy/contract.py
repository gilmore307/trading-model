"""Current physical constants for Layer 6 DynamicRiskPolicyModel."""
from __future__ import annotations

from typing import Final

MODEL_ID: Final[str] = "dynamic_risk_policy_model"
MODEL_LAYER: Final[str] = "layer_06_dynamic_risk_policy"
MODEL_SURFACE: Final[str] = "model_06_dynamic_risk_policy"
MODEL_VERSION: Final[str] = "dynamic_risk_policy_state_contract"
VECTOR_OUTPUT: Final[str] = "dynamic_risk_policy_state"
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")
SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "6_dynamic_risk_budget_score_<horizon>",
    "6_premium_budget_score_<horizon>",
    "6_new_exposure_permission_score_<horizon>",
    "6_market_stress_haircut_score_<horizon>",
    "6_systemic_event_haircut_score_<horizon>",
    "6_portfolio_capacity_score_<horizon>",
    "6_policy_stability_score_<horizon>",
    "6_risk_policy_confidence_score_<horizon>",
)
RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "6_resolved_dynamic_risk_budget_score",
    "6_resolved_premium_budget_score",
    "6_resolved_new_exposure_permission_score",
    "6_resolved_risk_policy_horizon",
    "6_risk_policy_reason_codes",
)
FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset({
    "buy", "sell", "hold", "open", "close", "reverse", "order_quantity", "order_type",
    "route", "broker_order_id", "option_contract", "option_symbol", "strike", "dte",
    "delta", "gamma", "theta", "vega", "final_action", "execution_instruction",
    "future_return", "future_fill", "realized_pnl", "hard_limit_override",
})

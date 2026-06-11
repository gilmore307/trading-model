"""Contract constants for M06 ResidualEventGovernanceModel."""

from __future__ import annotations

from typing import Final

MODEL_STEP: Final[str] = "M06"
MODEL_ID: Final[str] = "residual_event_governance_model"
MODEL_SURFACE: Final[str] = "model_06_residual_event_governance"
CONCEPTUAL_OUTPUT: Final[str] = "event_risk_intervention"
MODEL_VERSION: Final[str] = "event_risk_intervention_contract"
PRIMARY_OUTPUT: Final[str] = CONCEPTUAL_OUTPUT
HORIZONS: Final[tuple[str, ...]] = ("10min", "1h", "1D", "1W")

EVENT_IMPACT_CHANNELS: Final[tuple[str, ...]] = (
    "underlying_price",
    "option_price",
    "volatility_surface",
    "option_liquidity_spread",
    "expiry_gamma_flow",
)

OPTION_SENSITIVE_EVENT_FAMILIES: Final[tuple[str, ...]] = (
    "triple_witching_calendar",
    "monthly_option_expiration",
    "earnings_iv_crush",
    "index_rebalance_expiry_flow",
    "volatility_surface_dislocation",
)

CORE_SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "6_event_presence_score_<horizon>",
    "6_event_timing_proximity_score_<horizon>",
    "6_event_intensity_score_<horizon>",
    "6_event_direction_bias_score_<horizon>",
    "6_event_context_alignment_score_<horizon>",
    "6_event_uncertainty_score_<horizon>",
    "6_event_gap_risk_score_<horizon>",
    "6_event_reversal_risk_score_<horizon>",
    "6_event_liquidity_disruption_score_<horizon>",
    "6_event_contagion_risk_score_<horizon>",
    "6_event_context_quality_score_<horizon>",
)

IMPACT_SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "6_event_market_impact_score_<horizon>",
    "6_event_sector_impact_score_<horizon>",
    "6_event_industry_impact_score_<horizon>",
    "6_event_theme_factor_impact_score_<horizon>",
    "6_event_peer_group_impact_score_<horizon>",
    "6_event_symbol_impact_score_<horizon>",
    "6_event_microstructure_impact_score_<horizon>",
    "6_event_underlying_impact_score_<horizon>",
    "6_event_option_impact_score_<horizon>",
    "6_event_scope_confidence_score_<horizon>",
    "6_event_scope_escalation_risk_score_<horizon>",
    "6_event_target_relevance_score_<horizon>",
)

RESOLVED_FIELD_FAMILIES: Final[tuple[str, ...]] = (
    "6_resolved_intervention_action",
    "6_resolved_intervention_severity_score",
    "6_resolved_risk_horizon",
    "6_resolved_reason_codes",
)

INTERVENTION_ACTIONS: Final[tuple[str, ...]] = (
    "no_intervention",
    "warn",
    "cap_new_exposure",
    "block_new_entry",
    "reduce_or_flatten_review",
)

FORBIDDEN_OUTPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "underlying_action_plan",
        "underlying_action_vector",
        "underlying_action_plan_ref",
        "base_underlying_action_plan_ref",
        "event_context_vector",
        "event_context_vector_ref",
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
        "future_return",
        "future_price",
        "realized_pnl",
    }
)

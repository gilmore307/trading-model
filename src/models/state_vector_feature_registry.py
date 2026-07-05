"""Reviewed state-vector feature semantics registry.

The registry is intentionally small and explicit: it records the semantic class of
reviewed shared score fields so generator, evaluation, docs, and registry
migrations do not let direction, quality, risk, action intensity, routing,
diagnostics, and research-only fields blur together.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

ScoreClass = Literal[
    "direction",
    "direction_strength",
    "expected_return",
    "intensity",
    "quality",
    "risk",
    "liquidity",
    "routing",
    "diagnostic",
    "research",
]
FeatureUse = Literal["model_facing", "routing_only", "diagnostic_only", "research_only"]
HighValueMeaning = Literal["signed", "good", "bad", "count", "category", "identifier", "payload"]


@dataclass(frozen=True)
class FeatureSemantics:
    field_pattern: str
    layer: str
    dtype: str
    value_range: str
    score_class: ScoreClass
    high_value_meaning: HighValueMeaning
    feature_use: FeatureUse
    note: str


STATE_VECTOR_FEATURE_SEMANTICS: Final[tuple[FeatureSemantics, ...]] = (
    FeatureSemantics("1_market_direction_score_<horizon>", "model_01_background_context", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed broad-market direction evidence."),
    FeatureSemantics("1_market_trend_quality_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral market trend clarity."),
    FeatureSemantics("1_market_risk_stress_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "risk", "bad", "model_facing", "Market stress; high is worse."),
    FeatureSemantics("1_market_liquidity_support_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "liquidity", "good", "model_facing", "Liquidity support; high is better."),
    FeatureSemantics("1_market_volatility_pressure_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "risk", "bad", "model_facing", "Volatility pressure; high is worse."),
    FeatureSemantics("1_sector_breadth_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "quality", "good", "model_facing", "Sector breadth support inside the background context."),
    FeatureSemantics("1_sector_dispersion_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "quality", "good", "model_facing", "Cross-sectional sector dispersion/opportunity context."),
    FeatureSemantics("1_background_context_quality_score_<horizon>", "model_01_background_context", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "M01 context quality and coverage."),
    FeatureSemantics("2_target_direction_score_<horizon>", "model_02_target_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed target-state direction evidence."),
    FeatureSemantics("2_target_trend_quality_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral target trend quality."),
    FeatureSemantics("2_target_path_stability_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "quality", "good", "model_facing", "Target path smoothness and persistence."),
    FeatureSemantics("2_target_noise_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Noise/chop risk; high is worse."),
    FeatureSemantics("2_target_transition_risk_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Target state-transition risk; high is worse."),
    FeatureSemantics("2_context_support_quality_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "quality", "good", "model_facing", "Background/context support for the target state."),
    FeatureSemantics("2_tradability_score_<horizon>", "model_02_target_state", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral target tradability."),
    FeatureSemantics("3_event_response_direction_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed event response tendency."),
    FeatureSemantics("3_event_response_strength_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "direction_strength", "good", "model_facing", "Event response magnitude regardless of sign."),
    FeatureSemantics("3_event_uncertainty_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Event uncertainty; high is worse."),
    FeatureSemantics("3_event_path_risk_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Event-driven adverse path risk; high is worse."),
    FeatureSemantics("3_event_entry_block_pressure_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Pressure to block new entries; high is more restrictive."),
    FeatureSemantics("3_event_exposure_cap_pressure_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Pressure to cap exposure; high is more restrictive."),
    FeatureSemantics("3_event_strategy_disable_pressure_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Pressure to disable or downweight a strategy family."),
    FeatureSemantics("3_event_applicability_confidence_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence that event evidence applies to the target/context."),
    FeatureSemantics("3_event_underlying_price_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed event impact on underlying price."),
    FeatureSemantics("3_event_option_price_impact_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Option-price event sensitivity."),
    FeatureSemantics("3_event_volatility_surface_impact_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Volatility-surface event sensitivity."),
    FeatureSemantics("3_event_option_liquidity_spread_impact_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "liquidity", "bad", "model_facing", "Option liquidity/spread disruption pressure."),
    FeatureSemantics("3_event_expiry_gamma_flow_impact_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Expiry/gamma-flow event sensitivity."),
    FeatureSemantics("3_event_market_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed market-scope event impact."),
    FeatureSemantics("3_event_sector_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed sector-scope event impact."),
    FeatureSemantics("3_event_industry_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed industry-scope event impact."),
    FeatureSemantics("3_event_theme_factor_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed theme/factor-scope event impact."),
    FeatureSemantics("3_event_peer_group_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed peer-group event impact."),
    FeatureSemantics("3_event_symbol_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed symbol-scope event impact; not ticker identity memorization."),
    FeatureSemantics("3_event_microstructure_impact_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed microstructure-scope event impact."),
    FeatureSemantics("3_event_scope_confidence_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence in assigned event impact scope."),
    FeatureSemantics("3_event_scope_escalation_risk_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Risk that event impact spreads beyond current scope; high is worse."),
    FeatureSemantics("3_event_target_relevance_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "quality", "good", "model_facing", "Relevance of visible event evidence to the target context."),
    FeatureSemantics("3_event_mean_shift_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Reviewed event-family permissioned mean shift; default is zero."),
    FeatureSemantics("3_event_mode_shift_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Reviewed event-family permissioned mode shift; default is zero."),
    FeatureSemantics("3_event_directional_contribution_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Reviewed directional event contribution after M01/M02 controls."),
    FeatureSemantics("3_event_variance_multiplier_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Event-driven variance expansion pressure."),
    FeatureSemantics("3_event_left_tail_delta_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Event-driven adverse left-tail expansion."),
    FeatureSemantics("3_event_right_tail_delta_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "quality", "good", "model_facing", "Event-driven favorable right-tail expansion."),
    FeatureSemantics("3_event_skew_delta_score_<horizon>", "model_03_event_state", "float", "[-1, 1]", "direction", "signed", "model_facing", "Event-driven distribution skew adjustment."),
    FeatureSemantics("3_event_confidence_discount_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "quality", "bad", "model_facing", "Event-driven confidence discount pressure."),
    FeatureSemantics("3_event_gate_pressure_score_<horizon>", "model_03_event_state", "float", "[0, 1]", "risk", "bad", "model_facing", "Event-driven pressure for no-entry or stricter eligibility."),
    FeatureSemantics("4_edge_direction_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed decision edge direction."),
    FeatureSemantics("4_direction_thesis_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed path thesis direction before direct-underlying eligibility."),
    FeatureSemantics("4_direction_certainty_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "direction_strength", "good", "model_facing", "Direction certainty independent of bullish or bearish sign."),
    FeatureSemantics("4_after_cost_edge_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "expected_return", "good", "model_facing", "After-cost normalized edge; high is better."),
    FeatureSemantics("4_expected_return_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "expected_return", "signed", "model_facing", "Signed expected return evidence."),
    FeatureSemantics("4_edge_confidence_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence in the decision edge."),
    FeatureSemantics("4_downside_risk_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "risk", "bad", "model_facing", "Expected adverse path and downside pressure."),
    FeatureSemantics("4_risk_budget_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Risk budget fit for a candidate decision."),
    FeatureSemantics("4_new_exposure_permission_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Permission pressure for new exposure; not final execution approval."),
    FeatureSemantics("4_target_exposure_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "intensity", "signed", "model_facing", "Abstract target exposure; not shares, contracts, or an order quantity."),
    FeatureSemantics("4_target_allocation_fraction_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "intensity", "good", "model_facing", "Target allocation fraction of total budget for new entry sizing."),
    FeatureSemantics("4_position_gap_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "direction", "signed", "model_facing", "Target-current exposure gap; positive same-direction gaps do not create add orders."),
    FeatureSemantics("4_trade_intensity_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "intensity", "good", "model_facing", "Trade materiality after context, cost, and risk evidence."),
    FeatureSemantics("4_materiality_adjusted_action_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "intensity", "good", "model_facing", "Action strength after materiality and no-trade probability."),
    FeatureSemantics("4_no_trade_probability_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "risk", "bad", "model_facing", "Probability that no new operation is the better choice."),
    FeatureSemantics("4_action_eligibility_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Eligibility for a model-side action thesis."),
    FeatureSemantics("4_action_direction_score_<horizon>", "model_04_unified_decision", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed direction of the model-side underlying thesis."),
    FeatureSemantics("4_entry_quality_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Entry quality for the thesis; not an order type."),
    FeatureSemantics("4_action_confidence_score_<horizon>", "model_04_unified_decision", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence in the final M04 action thesis."),
    FeatureSemantics("5_option_expression_eligibility_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Option-expression admissibility after M04 thesis, policy, option-chain, liquidity, IV, and risk constraints; not order approval."),
    FeatureSemantics("5_option_expression_direction_score_<horizon>", "model_05_option_expression", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed expression direction; positive call-side/bullish, negative put-side/bearish, and no-option baseline inherits the M04 underlying-equity thesis direction."),
    FeatureSemantics("5_option_contract_fit_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Overall fit of selected option contract candidate to M04 path thesis and option-expression constraints."),
    FeatureSemantics("5_option_liquidity_fit_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "liquidity", "good", "model_facing", "Option bid/ask, volume, and open-interest fit; high is more liquid/fillable under conservative assumptions."),
    FeatureSemantics("5_option_iv_fit_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Implied-volatility and IV-rank fit for the selected expression; high means IV is acceptable for premium risk."),
    FeatureSemantics("5_option_greek_fit_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Delta/Greek fit for expressing the M04 underlying path thesis without crossing into execution."),
    FeatureSemantics("5_option_reward_risk_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Premium-adjusted reward/risk quality for the offline option expression."),
    FeatureSemantics("5_option_theta_risk_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "risk", "bad", "model_facing", "Theta-decay pressure for the option expression; high is worse."),
    FeatureSemantics("5_option_fill_quality_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Conservative fill-quality estimate from spread/liquidity evidence; not a route or order type."),
    FeatureSemantics("5_option_expression_confidence_score_<horizon>", "model_05_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Calibrated confidence in the offline option-expression plan; not final approval or execution authorization."),
)


def semantics_by_field() -> dict[str, FeatureSemantics]:
    return {entry.field_pattern: entry for entry in STATE_VECTOR_FEATURE_SEMANTICS}


def validate_feature_semantics() -> None:
    seen: set[str] = set()
    for entry in STATE_VECTOR_FEATURE_SEMANTICS:
        if entry.field_pattern in seen:
            raise ValueError(f"duplicate feature semantics entry: {entry.field_pattern}")
        seen.add(entry.field_pattern)
        if entry.score_class == "direction" and entry.high_value_meaning != "signed":
            raise ValueError(f"direction feature must be signed: {entry.field_pattern}")
        if entry.score_class == "risk" and entry.high_value_meaning != "bad":
            raise ValueError(f"risk feature must be high-is-bad: {entry.field_pattern}")
        if entry.score_class == "research" and entry.feature_use != "research_only":
            raise ValueError(f"research feature must be research_only: {entry.field_pattern}")

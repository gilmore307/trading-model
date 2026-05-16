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
    FeatureSemantics("1_market_direction_score", "layer_01_market_regime", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed broad-market direction evidence only."),
    FeatureSemantics("1_market_direction_strength_score", "layer_01_market_regime", "float", "[0, 1]", "direction_strength", "good", "model_facing", "Absolute market direction evidence strength; high can be long or short context."),
    FeatureSemantics("1_market_trend_quality_score", "layer_01_market_regime", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral market trend clarity."),
    FeatureSemantics("1_market_stability_score", "layer_01_market_regime", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral market path/state stability."),
    FeatureSemantics("1_market_risk_stress_score", "layer_01_market_regime", "float", "[0, 1]", "risk", "bad", "model_facing", "Market stress; high is worse."),
    FeatureSemantics("1_market_transition_risk_score", "layer_01_market_regime", "float", "[0, 1]", "risk", "bad", "model_facing", "State-switching/transition risk; high is worse."),
    FeatureSemantics("1_breadth_participation_score", "layer_01_market_regime", "float", "[0, 1]", "quality", "good", "model_facing", "Market breadth participation; high means broader confirmation."),
    FeatureSemantics("1_correlation_crowding_score", "layer_01_market_regime", "float", "[0, 1]", "risk", "bad", "model_facing", "One-factor/crowding pressure, not the inverse of dispersion opportunity."),
    FeatureSemantics("1_dispersion_opportunity_score", "layer_01_market_regime", "float", "[0, 1]", "quality", "good", "model_facing", "Cross-sectional opportunity/dispersion, kept separate from crowding."),
    FeatureSemantics("1_market_liquidity_pressure_score", "layer_01_market_regime", "float", "[0, 1]", "liquidity", "bad", "model_facing", "Liquidity pressure; high is worse."),
    FeatureSemantics("1_market_liquidity_support_score", "layer_01_market_regime", "float", "[0, 1]", "liquidity", "good", "model_facing", "Liquidity support; high is better."),
    FeatureSemantics("1_coverage_score", "layer_01_market_regime", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Coverage/reliability, not alpha or tradability itself."),
    FeatureSemantics("1_data_quality_score", "layer_01_market_regime", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Input data quality/reliability."),
    FeatureSemantics("2_sector_relative_direction_score", "layer_02_sector_context", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed sector-vs-market direction evidence only."),
    FeatureSemantics("2_sector_trend_quality_score", "layer_02_sector_context", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral sector trend quality."),
    FeatureSemantics("2_sector_trend_stability_score", "layer_02_sector_context", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral sector path stability."),
    FeatureSemantics("2_sector_transition_risk_score", "layer_02_sector_context", "float", "[0, 1]", "risk", "bad", "model_facing", "Sector state transition risk; high is worse."),
    FeatureSemantics("2_market_context_support_score", "layer_02_sector_context", "float", "[-1, 1]", "quality", "signed", "model_facing", "Direction-aware support for current sector state; weak market can support short-bias sector."),
    FeatureSemantics("2_sector_breadth_confirmation_score", "layer_02_sector_context", "float", "[0, 1]", "quality", "good", "model_facing", "Sector internal confirmation."),
    FeatureSemantics("2_sector_internal_dispersion_score", "layer_02_sector_context", "float", "[0, 1]", "risk", "bad", "model_facing", "Internal dispersion/fragmentation; high makes context less clean."),
    FeatureSemantics("2_sector_crowding_risk_score", "layer_02_sector_context", "float", "[0, 1]", "risk", "bad", "model_facing", "Crowding/co-movement pressure; high is worse."),
    FeatureSemantics("2_sector_liquidity_tradability_score", "layer_02_sector_context", "float", "[0, 1]", "liquidity", "good", "model_facing", "Basket/candidate-pool execution friendliness."),
    FeatureSemantics("2_sector_tradability_score", "layer_02_sector_context", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral sector handoff quality."),
    FeatureSemantics("2_sector_handoff_state", "layer_02_sector_context", "text", "enum", "routing", "category", "routing_only", "Route selected/watch/blocked/insufficient_data; not a model evidence score."),
    FeatureSemantics("2_sector_handoff_bias", "layer_02_sector_context", "text", "enum", "routing", "category", "routing_only", "Route long_bias/short_bias/neutral/mixed separately from handoff state."),
    FeatureSemantics("2_sector_handoff_rank", "layer_02_sector_context", "integer", "rank", "routing", "count", "routing_only", "Priority rank, not a portfolio weight."),
    FeatureSemantics("2_eligibility_state", "layer_02_sector_context", "text", "enum", "routing", "category", "routing_only", "Hard/soft eligibility gate."),
    FeatureSemantics("2_state_quality_score", "layer_02_sector_context", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Row reliability, not opportunity."),
    FeatureSemantics("2_coverage_score", "layer_02_sector_context", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Coverage/reliability."),
    FeatureSemantics("2_data_quality_score", "layer_02_sector_context", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Input data quality."),
    FeatureSemantics("3_target_direction_score_<window>", "layer_03_target_state_vector", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed target state evidence; not alpha confidence."),
    FeatureSemantics("3_target_direction_strength_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "direction_strength", "good", "model_facing", "Absolute direction evidence strength; high can be long or short context."),
    FeatureSemantics("3_target_trend_quality_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral target trend quality."),
    FeatureSemantics("3_target_path_stability_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral path smoothness and persistence."),
    FeatureSemantics("3_target_noise_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "risk", "bad", "model_facing", "Noise/chop risk; high is worse."),
    FeatureSemantics("3_target_transition_risk_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "risk", "bad", "model_facing", "State transition risk; high is worse."),
    FeatureSemantics("3_target_state_persistence_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "quality", "good", "model_facing", "State persistence/age support, direction-neutral."),
    FeatureSemantics("3_target_exhaustion_risk_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "risk", "bad", "model_facing", "Late-trend/exhaustion risk; high is worse."),
    FeatureSemantics("3_target_liquidity_tradability_score", "layer_03_target_state_vector", "float", "[0, 1]", "liquidity", "good", "model_facing", "Target execution friendliness."),
    FeatureSemantics("3_context_direction_alignment_score_<window>", "layer_03_target_state_vector", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed context alignment, not quality by itself."),
    FeatureSemantics("3_context_support_quality_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral context support quality."),
    FeatureSemantics("3_tradability_score_<window>", "layer_03_target_state_vector", "float", "[0, 1]", "quality", "good", "model_facing", "Direction-neutral target state tradability; stable shorts can score highly."),
    FeatureSemantics("3_state_quality_score", "layer_03_target_state_vector", "float", "[0, 1]", "diagnostic", "good", "diagnostic_only", "Produced state-vector reliability."),
    FeatureSemantics("3_evidence_count", "layer_03_target_state_vector", "integer", "count", "diagnostic", "count", "diagnostic_only", "Usable evidence count."),
    FeatureSemantics("target_state_embedding", "layer_03_target_state_vector", "array<float>", "derived", "research", "payload", "research_only", "Research/diagnostic embedding; not first-version primary model input."),
    FeatureSemantics("state_cluster_id", "layer_03_target_state_vector", "text", "derived", "research", "identifier", "research_only", "Research/diagnostic cluster id; must be fit/assigned walk-forward if promoted."),
    FeatureSemantics("4_event_presence_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "intensity", "count", "model_facing", "Visible event presence by horizon; high means more event presence, not good/bad by itself."),
    FeatureSemantics("4_event_timing_proximity_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "intensity", "count", "model_facing", "Proximity to a sensitive event window; high means more immediate event pressure, not good/bad by itself."),
    FeatureSemantics("4_event_intensity_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "intensity", "count", "model_facing", "Information shock / attention intensity; high means stronger visible event pressure, not good/bad by itself."),
    FeatureSemantics("4_event_direction_bias_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed target-conditioned event bias; not alpha confidence."),
    FeatureSemantics("4_event_context_alignment_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed support/conflict between event evidence and current target context."),
    FeatureSemantics("4_event_uncertainty_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "risk", "bad", "model_facing", "Information uncertainty; high is worse."),
    FeatureSemantics("4_event_gap_risk_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "risk", "bad", "model_facing", "Jump/gap risk; high is worse."),
    FeatureSemantics("4_event_reversal_risk_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "risk", "bad", "model_facing", "Current-path reversal risk; high is worse."),
    FeatureSemantics("4_event_liquidity_disruption_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "liquidity", "bad", "model_facing", "Spread/depth/slippage disruption risk; high is worse."),
    FeatureSemantics("4_event_contagion_risk_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "risk", "bad", "model_facing", "Cross-scope transmission risk; high is worse."),
    FeatureSemantics("4_event_context_quality_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "quality", "good", "model_facing", "Event evidence quality and context completeness."),
    FeatureSemantics("4_event_market_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed market-scope event impact."),
    FeatureSemantics("4_event_sector_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed sector-scope event impact."),
    FeatureSemantics("4_event_industry_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed industry-scope event impact."),
    FeatureSemantics("4_event_theme_factor_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed theme/factor-scope event impact."),
    FeatureSemantics("4_event_peer_group_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed peer-group event impact."),
    FeatureSemantics("4_event_symbol_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed symbol-scope event impact; not ticker identity memorization."),
    FeatureSemantics("4_event_microstructure_impact_score_<horizon>", "layer_08_event_risk_governor", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed microstructure-scope event impact."),
    FeatureSemantics("4_event_scope_confidence_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence in assigned event impact scope."),
    FeatureSemantics("4_event_scope_escalation_risk_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "risk", "bad", "model_facing", "Risk that event impact spreads beyond current scope; high is worse."),
    FeatureSemantics("4_event_target_relevance_score_<horizon>", "layer_08_event_risk_governor", "float", "[0, 1]", "quality", "good", "model_facing", "Relevance of visible event evidence to the target context."),
    FeatureSemantics("5_alpha_direction_score_<horizon>", "layer_05_alpha_confidence", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed long/short alpha direction; not buy/sell/hold."),
    FeatureSemantics("5_alpha_strength_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "direction_strength", "good", "model_facing", "Absolute alpha strength regardless of direction sign."),
    FeatureSemantics("5_expected_return_score_<horizon>", "layer_05_alpha_confidence", "float", "[-1, 1]", "expected_return", "signed", "model_facing", "Signed residual expected return after market/sector baseline adjustment."),
    FeatureSemantics("5_alpha_confidence_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "quality", "good", "model_facing", "Model confidence in the alpha judgment."),
    FeatureSemantics("5_signal_reliability_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "quality", "good", "model_facing", "Historical out-of-sample reliability for similar signals."),
    FeatureSemantics("5_path_quality_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "quality", "good", "model_facing", "Expected path smoothness/tradability quality."),
    FeatureSemantics("5_reversal_risk_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "risk", "bad", "model_facing", "Risk that alpha direction is interrupted or reversed; high is worse."),
    FeatureSemantics("5_drawdown_risk_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "risk", "bad", "model_facing", "Adverse excursion / MAE / drawdown risk; high is worse."),
    FeatureSemantics("5_alpha_tradability_score_<horizon>", "layer_05_alpha_confidence", "float", "[0, 1]", "quality", "good", "model_facing", "Alpha-level suitability for Layer 6 position projection; not target exposure."),
    FeatureSemantics("6_target_position_bias_score_<horizon>", "layer_06_position_projection", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed target holding-direction bias; not buy/sell/hold."),
    FeatureSemantics("6_target_exposure_score_<horizon>", "layer_06_position_projection", "float", "[-1, 1]", "intensity", "signed", "model_facing", "Normalized abstract target risk exposure; not shares/contracts/order quantity."),
    FeatureSemantics("6_current_position_alignment_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "quality", "good", "model_facing", "Current plus pending exposure already aligns with projected target state."),
    FeatureSemantics("6_position_gap_score_<horizon>", "layer_06_position_projection", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed target-current exposure gap; not an execution instruction."),
    FeatureSemantics("6_position_gap_magnitude_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "intensity", "good", "model_facing", "Absolute normalized target-current exposure gap; not urgency by itself."),
    FeatureSemantics("6_expected_position_utility_score_<horizon>", "layer_06_position_projection", "float", "[-1, 1]", "expected_return", "signed", "model_facing", "Signed expected risk-adjusted net utility of the projected target state."),
    FeatureSemantics("6_cost_to_adjust_position_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "risk", "bad", "model_facing", "Relative cost pressure to close the position gap; high is worse."),
    FeatureSemantics("6_risk_budget_fit_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "quality", "good", "model_facing", "Compatibility with current risk budget and portfolio constraints."),
    FeatureSemantics("6_position_state_stability_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "quality", "good", "model_facing", "Stability of projected target holding state across alpha, horizon, cost, risk, and pending-order uncertainty."),
    FeatureSemantics("6_projection_confidence_score_<horizon>", "layer_06_position_projection", "float", "[0, 1]", "quality", "good", "model_facing", "Confidence in the Layer 6 alpha-to-position mapping; separate from Layer 5 alpha confidence."),
    FeatureSemantics("7_underlying_trade_eligibility_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "quality", "good", "model_facing", "Direct-underlying trade eligibility after hard/soft gates; not final approval or a broker order."),
    FeatureSemantics("7_underlying_action_direction_score_<horizon>", "layer_07_underlying_action", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed planned direct-underlying side; positive long-side, negative short-side, near zero maintain/no_trade."),
    FeatureSemantics("7_underlying_trade_intensity_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "intensity", "good", "model_facing", "Planned adjustment intensity after confidence, risk, cost, stability, and liquidity compression; not final order quantity."),
    FeatureSemantics("7_underlying_entry_quality_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "quality", "good", "model_facing", "Side-neutral planned entry quality; entry plan is not broker order type."),
    FeatureSemantics("7_underlying_expected_return_score_<horizon>", "layer_07_underlying_action", "float", "[-1, 1]", "expected_return", "signed", "model_facing", "Signed favorable direct-underlying return quality after context adjustment."),
    FeatureSemantics("7_underlying_adverse_risk_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "risk", "bad", "model_facing", "Expected adverse move / stop-risk pressure; high is worse."),
    FeatureSemantics("7_underlying_reward_risk_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "quality", "good", "model_facing", "Reward/risk quality of the offline direct-underlying thesis."),
    FeatureSemantics("7_underlying_liquidity_fit_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "liquidity", "good", "model_facing", "Direct-underlying liquidity/spread fit for the planned adjustment."),
    FeatureSemantics("7_underlying_holding_time_fit_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "quality", "good", "model_facing", "Compatibility between planned holding time and alpha/projection/path evidence."),
    FeatureSemantics("7_underlying_action_confidence_score_<horizon>", "layer_07_underlying_action", "float", "[0, 1]", "quality", "good", "model_facing", "Calibrated confidence in the complete offline direct-underlying action thesis."),
    FeatureSemantics("8_option_expression_eligibility_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Option-expression admissibility after Layer 7 thesis, policy, option-chain, liquidity, IV, and risk constraints; not order approval."),
    FeatureSemantics("8_option_expression_direction_score_<horizon>", "layer_08_option_expression", "float", "[-1, 1]", "direction", "signed", "model_facing", "Signed option-expression direction; positive call-side/bullish, negative put-side/bearish, near zero no-option expression."),
    FeatureSemantics("8_option_contract_fit_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Overall fit of selected option contract candidate to Layer 7 path thesis and option-expression constraints."),
    FeatureSemantics("8_option_liquidity_fit_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "liquidity", "good", "model_facing", "Option bid/ask, volume, and open-interest fit; high is more liquid/fillable under conservative assumptions."),
    FeatureSemantics("8_option_iv_fit_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Implied-volatility and IV-rank fit for the selected expression; high means IV is acceptable for premium risk."),
    FeatureSemantics("8_option_greek_fit_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Delta/Greek fit for expressing the Layer 7 underlying path thesis without crossing into execution."),
    FeatureSemantics("8_option_reward_risk_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Premium-adjusted reward/risk quality for the offline option expression."),
    FeatureSemantics("8_option_theta_risk_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "risk", "bad", "model_facing", "Theta-decay pressure for the option expression; high is worse."),
    FeatureSemantics("8_option_fill_quality_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Conservative fill-quality estimate from spread/liquidity evidence; not a route or order type."),
    FeatureSemantics("8_option_expression_confidence_score_<horizon>", "layer_08_option_expression", "float", "[0, 1]", "quality", "good", "model_facing", "Calibrated confidence in the offline option-expression plan; not final approval or execution authorization."),
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

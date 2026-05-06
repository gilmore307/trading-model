"""Reviewed state-vector feature semantics registry.

The registry is intentionally small and explicit: it records the semantic class of
shared Layer 1/2/3 score fields so generator, evaluation, docs, and registry
migrations do not let direction, quality, risk, routing, diagnostics, and
research-only fields blur together.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

ScoreClass = Literal["direction", "direction_strength", "quality", "risk", "liquidity", "routing", "diagnostic", "research"]
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

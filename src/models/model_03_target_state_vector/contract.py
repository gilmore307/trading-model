"""Layer 3 TargetStateVectorModel contract constants."""
from __future__ import annotations

from typing import Final

LAYER3_PREPROCESSING_VECTOR: Final[str] = "anonymous_target_feature_vector"
LAYER3_OUTPUT_STATE_VECTOR: Final[str] = "target_context_state"

STATE_VECTOR_BLOCKS: Final[tuple[str, ...]] = (
    "market_state_features",
    "sector_state_features",
    "target_state_features",
    "cross_state_features",
)

MARKET_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "market_regime_state",
    "market_trend_state",
    "market_volatility_state",
    "market_breadth_state",
    "market_liquidity_stress_state",
    "market_correlation_state",
)

SECTOR_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "sector_context_state",
    "sector_relative_direction_state",
    "sector_trend_quality_stability_state",
    "sector_volatility_state",
    "sector_breadth_dispersion_state",
    "sector_liquidity_tradability_state",
)

TARGET_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "target_price_state",
    "target_direction_return_shape",
    "target_trend_quality_state",
    "target_trend_age_state",
    "target_exhaustion_decay_state",
    "target_volatility_range_state",
    "target_gap_jump_state",
    "target_volume_activity_state",
    "target_liquidity_tradability_state",
    "target_vwap_location_state",
    "target_session_position_state",
    "target_peer_rank_state",
    "target_shortability_state",
    "target_option_chain_state",
    "target_event_risk_state",
    "target_data_quality_state",
)

OPTION_CHAIN_STATE_SOURCE: Final[str] = "ThetaData"

OPTION_CHAIN_EXPIRY_BUCKETS: Final[tuple[tuple[str, int, int, str], ...]] = (
    ("short", 0, 6, "short_expiry_pressure_overlay"),
    ("front", 7, 45, "canonical_state"),
    ("near", 46, 90, "canonical_state"),
    ("mid", 91, 180, "canonical_state"),
)

OPTION_CHAIN_MONEYNESS_BUCKETS: Final[tuple[tuple[str, str], ...]] = (
    ("atm", "nearest_strike_to_spot_prefer_abs_delta_0_45_to_0_55"),
    ("canonical_call_wing", "prefer_call_abs_delta_0_20_to_0_35_else_5pct_otm_call"),
    ("canonical_put_wing", "prefer_put_abs_delta_0_20_to_0_35_else_5pct_otm_put"),
    ("round_activity_attention", "round_strike_near_spot_point_in_time_attention_candidate"),
    ("oi_activity_attention", "point_in_time_open_interest_attention_candidate_when_observable"),
)

OPTION_CHAIN_STATE_GROUPS: Final[tuple[str, ...]] = (
    "target_option_liquidity_state",
    "target_iv_pressure_state",
    "target_option_skew_pressure_state",
    "target_option_term_structure_pressure_state",
    "target_option_flow_pressure_state",
    "target_short_expiry_pressure_overlay",
)

OPTION_CHAIN_DIAGNOSTIC_FIELDS: Final[tuple[str, ...]] = (
    "option_quote_available_ratio",
    "option_trade_available_ratio",
    "option_iv_available_ratio",
    "option_greeks_available_ratio",
    "option_chain_observability_score",
    "option_liquidity_quality_score",
    "option_chain_snapshot_ref",
)

CROSS_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "target_vs_market_residual_direction",
    "target_vs_sector_residual_direction",
    "target_vs_market_volatility",
    "target_vs_sector_volatility",
    "target_market_beta_correlation",
    "target_sector_beta_correlation",
    "sector_confirmation_state",
    "idiosyncratic_residual_state",
    "relative_liquidity_tradability_state",
)

SYNCHRONIZED_STATE_WINDOWS: Final[tuple[str, ...]] = (
    "10min",
    "1h",
    "1D",
    "1W",
)

TRAILING_STATE_WINDOWS: Final[tuple[str, ...]] = SYNCHRONIZED_STATE_WINDOWS

LABEL_HORIZONS: Final[tuple[str, ...]] = (
    "10min",
    "1h",
    "1D",
    "1W",
)

TRAINING_LABEL_FAMILIES: Final[tuple[str, ...]] = (
    "future_tradeable_path",
    "forward_path_risk",
    "liquidity_tradability_outcome",
    "state_transition_quality",
)

DIRECTION_NEUTRAL_SCORE_FAMILIES: Final[tuple[str, ...]] = (
    "3_target_direction_score_<window>",
    "3_target_direction_strength_score_<window>",
    "3_target_trend_quality_score_<window>",
    "3_target_path_stability_score_<window>",
    "3_target_noise_score_<window>",
    "3_target_transition_risk_score_<window>",
    "3_target_state_persistence_score_<window>",
    "3_target_exhaustion_risk_score_<window>",
    "3_target_liquidity_tradability_score",
    "3_option_liquidity_score",
    "3_option_observability_score",
    "3_option_iv_pressure_score",
    "3_option_signed_skew_pressure_score",
    "3_option_term_structure_pressure_score",
    "3_option_signed_flow_pressure_score",
    "3_context_direction_alignment_score_<window>",
    "3_context_support_quality_score_<window>",
    "3_tradability_score_<window>",
    "3_state_quality_score",
)

BASELINE_LADDER: Final[tuple[str, ...]] = (
    "market_only_baseline",
    "market_sector_baseline",
    "market_sector_target_context",
)

MODEL_FACING_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "available_time",
    "tradeable_time",
    "target_candidate_id",
    "target_context_state_version",
    "market_context_state_ref",
    "sector_context_state_ref",
    "target_context_state_ref",
)

FORBIDDEN_MODEL_FACING_FIELDS: Final[tuple[str, ...]] = (
    "ticker",
    "symbol",
    "company",
    "audit_symbol_ref",
    "routing_symbol_ref",
    "future_return",
    "realized_pnl",
    "strategy_variant",
    "alpha_confidence",
    "position_size",
    "final_action",
    "option_contract",
    "option_contract_id",
    "option_contract_candidates",
    "option_chain",
    "option_chain_snapshot_id",
    "option_chain_snapshot_ref",
    "occ_symbol",
    "option_symbol",
    "contract_symbol",
    "strike",
    "expiry",
    "expiration",
    "dte",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "premium",
    "bid",
    "ask",
    "quote",
    "iv",
    "implied_volatility",
)

STATE_WINDOW_SYNC_POLICY: Final[str] = "market_sector_target_blocks_must_share_identical_observation_windows"

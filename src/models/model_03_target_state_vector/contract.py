"""Layer 3 TargetStateVectorModel V1 contract constants."""
from __future__ import annotations

from typing import Final

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
    "sector_relative_strength_state",
    "sector_trend_stability_state",
    "sector_volatility_state",
    "sector_breadth_dispersion_state",
    "sector_liquidity_tradability_state",
)

TARGET_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "target_return_shape",
    "target_trend_momentum_state",
    "target_volatility_range_state",
    "target_gap_jump_state",
    "target_volume_activity_state",
    "target_liquidity_cost_state",
    "target_vwap_location_state",
    "target_session_position_state",
    "target_data_quality_state",
)

CROSS_STATE_FEATURE_GROUPS: Final[tuple[str, ...]] = (
    "target_vs_market_strength",
    "target_vs_sector_strength",
    "target_vs_market_volatility",
    "target_vs_sector_volatility",
    "target_market_beta_correlation",
    "target_sector_beta_correlation",
    "sector_confirmation_state",
    "idiosyncratic_residual_state",
    "relative_liquidity_cost_state",
)

SYNCHRONIZED_STATE_WINDOWS: Final[tuple[str, ...]] = (
    "5min",
    "15min",
    "60min",
    "390min",
)

TRAILING_STATE_WINDOWS: Final[tuple[str, ...]] = SYNCHRONIZED_STATE_WINDOWS

LABEL_HORIZONS: Final[tuple[str, ...]] = (
    "15min",
    "60min",
    "390min",
)

BASELINE_LADDER: Final[tuple[str, ...]] = (
    "market_only_baseline",
    "market_sector_baseline",
    "market_sector_target_vector",
)

MODEL_FACING_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "available_time",
    "tradeable_time",
    "target_candidate_id",
    "target_state_vector_version",
    "market_context_state_ref",
    "sector_context_state_ref",
    "target_state_vector_ref",
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
)

STATE_WINDOW_SYNC_POLICY: Final[str] = "market_sector_target_blocks_must_share_identical_observation_windows"

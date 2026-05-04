"""Reviewed StrategySelectionModel standalone strategy families."""
from __future__ import annotations

from .common import StrategyFamilySpec, VariantAxis, family_payload, stable_spec_hash
from .moving_average_crossover import SPEC as moving_average_crossover
from .donchian_channel_breakout import SPEC as donchian_channel_breakout
from .macd_trend import SPEC as macd_trend
from .bollinger_band_reversion import SPEC as bollinger_band_reversion
from .rsi_reversion import SPEC as rsi_reversion
from .bias_reversion import SPEC as bias_reversion
from .vwap_reversion import SPEC as vwap_reversion
from .range_breakout import SPEC as range_breakout
from .opening_range_breakout import SPEC as opening_range_breakout
from .volatility_breakout import SPEC as volatility_breakout

ACTIVE_STANDALONE_FAMILIES: tuple[StrategyFamilySpec, ...] = (
    moving_average_crossover,
    donchian_channel_breakout,
    macd_trend,
    bollinger_band_reversion,
    rsi_reversion,
    bias_reversion,
    vwap_reversion,
    range_breakout,
    opening_range_breakout,
    volatility_breakout,
)

FAMILIES_BY_NAME = {spec.family: spec for spec in ACTIVE_STANDALONE_FAMILIES}

__all__ = [
    "ACTIVE_STANDALONE_FAMILIES",
    "FAMILIES_BY_NAME",
    "StrategyFamilySpec",
    "VariantAxis",
    "family_payload",
    "stable_spec_hash",
]

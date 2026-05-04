"""Reviewed StrategySelectionModel standalone strategy families."""
from __future__ import annotations

from .family_00_common import PRUNING_UNIT, StrategyFamilySpec, VariantAxis, family_payload, stable_spec_hash
from .family_01_moving_average_crossover import SPEC as moving_average_crossover
from .family_02_donchian_channel_breakout import SPEC as donchian_channel_breakout
from .family_03_macd_trend import SPEC as macd_trend
from .family_04_bollinger_band_reversion import SPEC as bollinger_band_reversion
from .family_05_rsi_reversion import SPEC as rsi_reversion
from .family_06_bias_reversion import SPEC as bias_reversion
from .family_07_vwap_reversion import SPEC as vwap_reversion
from .family_08_range_breakout import SPEC as range_breakout
from .family_09_opening_range_breakout import SPEC as opening_range_breakout
from .family_10_volatility_breakout import SPEC as volatility_breakout

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
FAMILY_EVALUATION_ORDER = tuple(spec.family for spec in ACTIVE_STANDALONE_FAMILIES)

__all__ = [
    "ACTIVE_STANDALONE_FAMILIES",
    "FAMILIES_BY_NAME",
    "FAMILY_EVALUATION_ORDER",
    "PRUNING_UNIT",
    "StrategyFamilySpec",
    "VariantAxis",
    "family_payload",
    "stable_spec_hash",
]

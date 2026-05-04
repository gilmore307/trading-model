"""volatility_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_00_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='volatility_breakout',
    evaluation_order=10,
    status=ACTIVE_CATALOG,
    summary='Trade when volatility expands enough to suggest a new directional move.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={'cooldown_bars': 1, 'volatility_cooloff_threshold': 'family_default_by_timeframe'},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('volatility_spec', ('ATR14_x1.25', 'ATR14_x1.5', 'ATR20_x1.5', 'HV20_x1.5', 'HV30_x2.0')),
        VariantAxis('direction_filter', ('none', 'trend', 'range_break')),
        VariantAxis('confirmation_bars', (1, 2)),
        VariantAxis('stop_atr_multiple', (1.5, 2.5)),
    ),
    notes=('Expansion alone does not guarantee directional edge; directionless variants are evaluated cautiously.',),
)

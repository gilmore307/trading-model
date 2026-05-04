"""donchian_channel_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_00_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='donchian_channel_breakout',
    group='trend_following',
    evaluation_order=2,
    status=ACTIVE_CATALOG,
    summary='Follow price when it breaks a prior high/low channel.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'breakout_side': 'both', 'atr_window': 14, 'retest_allowed': False, 'cooldown_bars': 1},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('entry_channel_window', (20, 55)),
        VariantAxis('exit_channel_window', (10, 20)),
        VariantAxis('breakout_buffer_atr', (0, 0.25, 0.5)),
        VariantAxis('confirmation_bars', (1, 2)),
        VariantAxis('stop_atr_multiple', (1.5, 2.5, 3.5)),
    ),
    notes=('stop_atr_multiple is setup/invalidation context only; execution stops are downstream.',),
)

"""range_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='range_breakout',
    evaluation_order=8,
    status=ACTIVE_CATALOG,
    summary='Trade a confirmed escape from a recent consolidation range.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={'breakout_direction': 'both', 'close_confirmation': True, 'failed_breakout_timeout': 'family_default_by_timeframe', 'cooldown_bars': 1},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('range_lookback', (20, 40, 60)),
        VariantAxis('range_width_max_atr', (1.0, 1.5, 2.0)),
        VariantAxis('breakout_buffer_atr', (0, 0.25, 0.5)),
        VariantAxis('volume_confirmation_ratio', (1.0, 1.5)),
        VariantAxis('retest_rule', ('none', 'allow_once')),
    ),
    notes=('Range width caps prevent labeling already-expanded moves as range breaks.',),
)

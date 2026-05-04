"""rsi_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_00_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='rsi_reversion',
    group='mean_reversion',
    evaluation_order=5,
    status=ACTIVE_CATALOG,
    summary='Fade overbought/oversold momentum extremes, optionally requiring divergence or higher-timeframe confirmation.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'price_field': 'bar_close', 'max_hold_bars': 'family_default_by_timeframe', 'cooldown_bars': 1},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('rsi_period', (7, 14, 21)),
        VariantAxis('threshold_pair', ((30, 70), (25, 75), (20, 80))),
        VariantAxis('exit_midline', ('45_55_band', '50_cross')),
        VariantAxis('divergence_required', (False, True)),
        VariantAxis('multi_timeframe_confirm', (False, True)),
    ),
    notes=('Divergence detection must be deterministic and point-in-time.',),
)

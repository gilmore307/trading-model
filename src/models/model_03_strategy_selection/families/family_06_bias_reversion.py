"""bias_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_00_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='bias_reversion',
    group='mean_reversion',
    evaluation_order=6,
    status=ACTIVE_CATALOG,
    summary='Fade large deviations from a moving average or z-score baseline.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'price_field': 'bar_close', 'max_hold_bars': 'family_default_by_timeframe'},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('ma_window', (20, 50)),
        VariantAxis('ma_type', ('sma', 'ema')),
        VariantAxis('deviation_measure', ('pct_from_ma', 'zscore_from_ma')),
        VariantAxis('entry_deviation_threshold', (1.5, 2.0, 2.5)),
        VariantAxis('exit_deviation_threshold', (0.25, 0.5)),
        VariantAxis('trend_filter_enabled', (False, True)),
    ),
    notes=('Threshold semantics stay explicit in variable_parameters.',),
)

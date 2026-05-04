"""moving_average_crossover standalone strategy-family spec."""
from __future__ import annotations

from .common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='moving_average_crossover',
    group='trend_following',
    status=ACTIVE_CATALOG,
    summary='Follow trend changes when a faster moving average crosses a slower moving average.',
    suitable_periods=('30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'price_field': 'bar_close', 'exit_rule': 'opposite_cross_or_score_decay', 'cooldown_bars': 1},
    axes=(
        VariantAxis('timeframe', ('30Min', '1Hour', '1Day')),
        VariantAxis('ma_pair', ((5, 20), (10, 30), (20, 50), (50, 200))),
        VariantAxis('ma_type', ('sma', 'ema')),
        VariantAxis('crossover_confirmation_bars', (1, 2, 3)),
        VariantAxis('min_slope', (0, 0.05)),
        VariantAxis('trend_filter_enabled', (False, True)),
    ),
    notes=('fast_window < slow_window is enforced through curated ma_pair values.',),
)

"""moving_average_crossover standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='moving_average_crossover',
    evaluation_order=1,
    status=ACTIVE_CATALOG,
    summary='Follow trend changes when a faster moving average crosses a slower moving average.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar_1min',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'price_field': 'bar_close',
        'exit_rule': 'opposite_cross_or_score_decay',
        'cooldown_bars': 1,
    },
    axes=(
        VariantAxis('ma_window_minutes', ((30, 120), (60, 240), (120, 480), (300, 1200))),
        VariantAxis('ma_type', ('sma', 'ema')),
        VariantAxis('crossover_confirmation_bars', (1, 2, 3)),
        VariantAxis('min_slope', (0, 0.05)),
        VariantAxis('trend_filter_enabled', (False, True)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'fast_window_minutes < slow_window_minutes is enforced through curated ma_window_minutes values.',
    ),
)

"""moving_average_crossover standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='moving_average_crossover',
    evaluation_order=1,
    status=ACTIVE_CATALOG,
    summary='Follow trend changes when a faster moving average crosses a slower moving average.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'exit_rule': 'opposite_cross_or_score_decay',
    },
    axes=(
        VariantAxis(
            'ma_window_profile',
            (
                ('micro_3_10', 3, 10),
                ('scalp_5_20', 5, 20),
                ('fast_10_30', 10, 30),
                ('intraday_30_120', 30, 120),
                ('intraday_90_360', 90, 360),
                ('intraday_240_960', 240, 960),
                ('equity_day_390_1950', 390, 1950),
                ('continuous_day_1440_7200', 1440, 7200),
            ),
        ),
        VariantAxis('price_field', ('bar_close', 'bar_hlc3')),
        VariantAxis('ma_type', ('ema', 'sma')),
        VariantAxis('crossover_confirmation_bars', (1, 2, 3)),
        VariantAxis('cooldown_bars', (1, 3, 5)),
        VariantAxis('min_slope', (0.01, 0.03, 0.05)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'ma_window_profile values are tuples of (profile_id, fast_window_1min_bars, slow_window_1min_bars).',
        'fast_window_1min_bars < slow_window_1min_bars is enforced through curated ma_window_profile values.',
        'The initial profile grid is intentionally sparse; add intermediate profiles only when evaluation finds stable uncovered performance between adjacent windows.',
        'The reviewed 864-variant grid is an accepted exception to the normal 500-variant standalone family cap.',
        'Market/sector context should affect strategy selection outside this simple crossover family, not through an embedded trend filter axis.',
    ),
)

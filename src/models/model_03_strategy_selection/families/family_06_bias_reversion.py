"""bias_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='bias_reversion',
    evaluation_order=6,
    status=ACTIVE_CATALOG,
    summary='Fade large deviations from a moving average or z-score baseline.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'price_field': 'bar_close',
        'max_hold_minutes': 'family_default_by_profile',
    },
    axes=(
        VariantAxis('ma_window_profile', (
            ('micro_10', 10), ('scalp_20', 20), ('fast_30', 30), ('intraday_60', 60),
            ('intraday_120', 120), ('intraday_240', 240), ('equity_day_390', 390), ('continuous_day_1440', 1440),
        )),
        VariantAxis('ma_type', ('sma', 'ema')),
        VariantAxis('deviation_measure', ('pct_from_ma', 'zscore_from_ma')),
        VariantAxis('entry_deviation_threshold', (1.5, 2.0, 2.5)),
        VariantAxis('exit_deviation_threshold', (0.25, 0.5)),
        VariantAxis('trend_filter_enabled', (False, True)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'ma_window_profile values are tuples of (profile_id, ma_window_1min_bars).',
        'Threshold semantics stay explicit in variable_parameters.',
    ),
)

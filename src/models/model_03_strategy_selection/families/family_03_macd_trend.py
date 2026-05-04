"""macd_trend standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='macd_trend',
    evaluation_order=3,
    status=ACTIVE_CATALOG,
    summary='Use MACD line, signal line, and histogram behavior to detect trend acceleration or reversal.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'price_field': 'bar_close',
        'trend_filter_window': 'inherited_from_variant_context_if_enabled_later',
        'cooldown_bars': 1,
    },
    axes=(
        VariantAxis(
            'macd_profile',
            (
                ('micro_3_10_3', 3, 10, 3),
                ('scalp_5_20_5', 5, 20, 5),
                ('fast_8_21_5', 8, 21, 5),
                ('intraday_12_26_9', 12, 26, 9),
                ('intraday_60_180_45', 60, 180, 45),
                ('intraday_240_720_180', 240, 720, 180),
                ('equity_day_390_1014_351', 390, 1014, 351),
                ('continuous_day_1440_3744_1296', 1440, 3744, 1296),
            ),
        ),
        VariantAxis('histogram_threshold', ('0', '0.25_atr_normalized')),
        VariantAxis('zero_line_filter', (False, True)),
        VariantAxis('slope_confirmation_bars', (1, 2, 3)),
        VariantAxis('exit_on_signal_cross', (False, True)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'macd_profile values are tuples of (profile_id, fast_ema_1min_bars, slow_ema_1min_bars, signal_ema_1min_bars).',
    ),
)

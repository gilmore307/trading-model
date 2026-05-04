"""donchian_channel_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='donchian_channel_breakout',
    evaluation_order=2,
    status=ACTIVE_CATALOG,
    summary='Follow price when it breaks a prior high/low channel.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'breakout_side': 'both',
        'retest_allowed': False,
        'cooldown_bars': 1,
    },
    axes=(
        VariantAxis(
            'channel_window_profile',
            (
                ('micro_10_5_atr10', 10, 5, 10),
                ('scalp_20_10_atr14', 20, 10, 14),
                ('fast_30_15_atr20', 30, 15, 20),
                ('intraday_60_30_atr30', 60, 30, 30),
                ('intraday_120_60_atr60', 120, 60, 60),
                ('intraday_240_120_atr120', 240, 120, 120),
                ('equity_day_390_195_atr195', 390, 195, 195),
                ('continuous_day_1440_720_atr720', 1440, 720, 720),
            ),
        ),
        VariantAxis('breakout_buffer_atr', (0, 0.25, 0.5)),
        VariantAxis('confirmation_bars', (1, 2)),
        VariantAxis('stop_atr_multiple', (1.5, 2.5, 3.5)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'channel_window_profile values are tuples of (profile_id, entry_channel_1min_bars, exit_channel_1min_bars, atr_window_1min_bars).',
        'stop_atr_multiple is setup/invalidation context only; execution stops are downstream.',
    ),
)

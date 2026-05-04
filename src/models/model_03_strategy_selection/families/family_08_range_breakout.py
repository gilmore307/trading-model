"""range_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='range_breakout',
    evaluation_order=8,
    status=ACTIVE_CATALOG,
    summary='Trade a confirmed escape from a recent consolidation range.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'breakout_direction': 'both',
        'close_confirmation': True,
        'failed_breakout_timeout_minutes': 'family_default_by_profile',
        'cooldown_bars': 1,
    },
    axes=(
        VariantAxis('range_window_profile', (
            ('micro_10', 10), ('scalp_20', 20), ('fast_30', 30), ('intraday_60', 60),
            ('intraday_120', 120), ('intraday_240', 240), ('equity_day_390', 390), ('continuous_day_1440', 1440),
        )),
        VariantAxis('range_width_max_atr', (1.0, 1.5, 2.0)),
        VariantAxis('breakout_buffer_atr', (0, 0.25, 0.5)),
        VariantAxis('volume_confirmation_ratio', (1.0, 1.5)),
        VariantAxis('retest_rule', ('none', 'allow_once')),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'range_window_profile values are tuples of (profile_id, range_lookback_1min_bars).',
        'Range width caps prevent labeling already-expanded moves as range breaks.',
    ),
)

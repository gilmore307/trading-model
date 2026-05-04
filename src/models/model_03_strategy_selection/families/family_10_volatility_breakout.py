"""volatility_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='volatility_breakout',
    evaluation_order=10,
    status=ACTIVE_CATALOG,
    summary='Trade when volatility expands enough to suggest a new directional move.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'cooldown_bars': 1,
        'volatility_cooloff_threshold': 'family_default_by_profile',
    },
    axes=(
        VariantAxis('volatility_profile', (
            ('micro_atr10_x1.25', 'ATR', 10, 1.25),
            ('scalp_atr14_x1.5', 'ATR', 14, 1.5),
            ('fast_atr20_x1.5', 'ATR', 20, 1.5),
            ('intraday_atr60_x1.5', 'ATR', 60, 1.5),
            ('intraday_atr120_x2.0', 'ATR', 120, 2.0),
            ('intraday_hv240_x1.5', 'HV', 240, 1.5),
            ('equity_day_atr390_x1.5', 'ATR', 390, 1.5),
            ('continuous_day_hv1440_x2.0', 'HV', 1440, 2.0),
        )),
        VariantAxis('direction_filter', ('none', 'trend', 'range_break')),
        VariantAxis('confirmation_bars', (1, 2)),
        VariantAxis('stop_atr_multiple', (1.5, 2.5)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'volatility_profile values are tuples of (profile_id, volatility_measure, volatility_window_1min_bars, expansion_threshold).',
        'Expansion alone does not guarantee directional edge; directionless variants are evaluated cautiously.',
    ),
)

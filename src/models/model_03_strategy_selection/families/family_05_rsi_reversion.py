"""rsi_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='rsi_reversion',
    evaluation_order=5,
    status=ACTIVE_CATALOG,
    summary='Fade overbought/oversold momentum extremes, optionally requiring divergence or higher-duration confirmation.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'price_field': 'bar_close',
        'max_hold_minutes': 'family_default_by_profile',
        'cooldown_bars': 1,
    },
    axes=(
        VariantAxis('rsi_period_profile', (
            ('micro_5', 5), ('fast_7', 7), ('scalp_14', 14), ('intraday_30', 30),
            ('intraday_60', 60), ('intraday_120', 120), ('equity_day_390', 390), ('continuous_day_1440', 1440),
        )),
        VariantAxis('threshold_pair', ((30, 70), (25, 75), (20, 80))),
        VariantAxis('exit_midline', ('45_55_band', '50_cross')),
        VariantAxis('divergence_required', (False, True)),
        VariantAxis('multi_duration_confirm', (False, True)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'rsi_period_profile values are tuples of (profile_id, rsi_period_1min_bars).',
        'Divergence detection must be deterministic and point-in-time.',
    ),
)

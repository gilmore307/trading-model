"""bollinger_band_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='bollinger_band_reversion',
    evaluation_order=4,
    status=ACTIVE_CATALOG,
    summary='Fade stretched prices back toward a volatility band center when context supports reversion.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'price_field': 'bar_close',
        'rsi_filter_period': 'optional_diagnostic_only_initially',
        'volatility_regime_filter': 'allowed_unless_extreme_trend',
    },
    axes=(
        VariantAxis('band_window_profile', (
            ('micro_10', 10), ('scalp_20', 20), ('fast_30', 30), ('intraday_60', 60),
            ('intraday_120', 120), ('intraday_240', 240), ('equity_day_390', 390), ('continuous_day_1440', 1440),
        )),
        VariantAxis('band_stddev', (1.5, 2.0, 2.5)),
        VariantAxis('entry_band', ('outer_touch', 'close_outside')),
        VariantAxis('exit_band', ('midline', 'half_sigma')),
        VariantAxis('trend_filter_enabled', (False, True)),
        VariantAxis('max_hold_minutes', (30, 120)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'band_window_profile values are tuples of (profile_id, window_1min_bars).',
        'max_hold_minutes is setup expiry/evaluation context, not an order instruction.',
    ),
)

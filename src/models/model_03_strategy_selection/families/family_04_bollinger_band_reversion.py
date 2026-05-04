"""bollinger_band_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='bollinger_band_reversion',
    evaluation_order=4,
    status=ACTIVE_CATALOG,
    summary='Fade stretched prices back toward a volatility band center when context supports reversion.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'price_field': 'bar_close', 'rsi_filter_period': 'optional_diagnostic_only_initially', 'volatility_regime_filter': 'allowed_unless_extreme_trend'},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('window', (20, 30)),
        VariantAxis('band_stddev', (1.5, 2.0, 2.5)),
        VariantAxis('entry_band', ('outer_touch', 'close_outside')),
        VariantAxis('exit_band', ('midline', 'half_sigma')),
        VariantAxis('trend_filter_enabled', (False, True)),
        VariantAxis('max_hold_bars', (10, 20)),
    ),
    notes=('max_hold_bars is setup expiry/evaluation context, not an order instruction.',),
)

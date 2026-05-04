"""macd_trend standalone strategy-family spec."""
from __future__ import annotations

from .family_00_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis

SPEC = StrategyFamilySpec(
    family='macd_trend',
    evaluation_order=3,
    status=ACTIVE_CATALOG,
    summary='Use MACD line, signal line, and histogram behavior to detect trend acceleration or reversal.',
    suitable_periods=('15Min', '30Min', '1Hour', '1Day'),
    alpaca_data_support=('equity_bar',),
    fixed_parameters={'price_field': 'bar_close', 'trend_filter_window': 'inherited_from_variant_context_if_enabled_later', 'cooldown_bars': 1},
    axes=(
        VariantAxis('timeframe', ('15Min', '30Min', '1Hour', '1Day')),
        VariantAxis('macd_spec', ((12, 26, 9), (8, 21, 5), (19, 39, 9))),
        VariantAxis('histogram_threshold', ('0', '0.25_atr_normalized')),
        VariantAxis('zero_line_filter', (False, True)),
        VariantAxis('slope_confirmation_bars', (1, 2, 3)),
        VariantAxis('exit_on_signal_cross', (False, True)),
    ),
    notes=('macd_spec expands to fast_ema_window, slow_ema_window, and signal_window during feature calculation.',),
)

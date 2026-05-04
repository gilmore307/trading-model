"""vwap_reversion standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='vwap_reversion',
    evaluation_order=7,
    status=ACTIVE_CATALOG,
    summary='Fade intraday price deviations back toward regular-session VWAP.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'vwap_scope': 'regular_session_vwap',
        'premarket_context_mode': 'context_filter',
        'earliest_entry_time': '10:00 ET',
        'no_trade_after_time': '15:30 ET',
        'minimum_dollar_volume': 'target_relative_liquidity_gate',
        'time_of_day_bucket': 'derived_label_not_variant_axis',
    },
    axes=(
        VariantAxis('deviation_bps', (30, 50, 75, 100)),
        VariantAxis('entry_zscore', (1.0, 1.5, 2.0)),
        VariantAxis('exit_zscore', (0.25, 0.5, 0.75)),
        VariantAxis('maximum_spread_bps', (5, 10, 15)),
    ),
    notes=(
        'All variants use completed 1Min bars; signal_timeframe is not a variant axis.',
        'Option chain and option liquidity checks belong to OptionExpressionModel.',
    ),
)

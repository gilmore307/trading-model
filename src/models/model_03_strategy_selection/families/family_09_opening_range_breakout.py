"""opening_range_breakout standalone strategy-family spec."""
from __future__ import annotations

from .family_spec_common import ACTIVE_CATALOG, StrategyFamilySpec, VariantAxis


SPEC = StrategyFamilySpec(
    family='opening_range_breakout',
    evaluation_order=9,
    status=ACTIVE_CATALOG,
    summary='Trade a regular-session break above/below the opening range.',
    suitable_periods=('unified_1min_bar_grid',),
    alpaca_data_support=('equity_bar', 'equity_liquidity_bar'),
    fixed_parameters={
        'signal_bar_interval': '1Min',
        'regular_session_open': '09:30 ET',
        'direction_mode': 'both',
        'first_trade_delay_minutes': 5,
        'time_stop_minutes': 60,
        'max_trades_per_session': 1,
        'premarket_context_mode': 'context_filter',
        'no_trade_after_time': '11:00 ET',
        'liquidity_filter': 'strict',
    },
    axes=(
        VariantAxis('opening_range_minutes', (5, 15, 30, 60)),
        VariantAxis('breakout_buffer_bps', (5, 10, 20)),
        VariantAxis('volume_confirmation_ratio', (1.0, 1.25, 1.5, 2.0)),
    ),
    notes=(
        'All variants use completed 1Min bars; timeframe is not a variant axis.',
        'Premarket can filter context but must not define the opening range.',
    ),
)

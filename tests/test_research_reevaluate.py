from src.research.reevaluate import reevaluate_strategy_row


def make_row():
    return {
        'timestamp': '2026-03-19T12:00:00+00:00',
        'symbol': 'BTC-USDT-SWAP',
        'bg_regime': 'trend',
        'bg_confidence': 0.8,
        'primary_regime': 'trend',
        'primary_confidence': 0.75,
        'override_regime': None,
        'override_confidence': None,
        'final_regime': 'trend',
        'final_confidence': 0.8,
        'route_account': 'trend',
        'route_strategy_family': 'trend',
        'route_trade_enabled': True,
        'decision_summary': {},
        'background_features': {'adx': 30.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
        'primary_features': {'adx': 26.0, 'vwap_deviation_z': 1.0, 'bollinger_bandwidth_pct': 0.1, 'realized_vol_pct': 0.005, 'funding_pctile': 0.6, 'oi_accel': 0.1, 'basis_deviation_pct': 0.001},
        'override_features': {'vwap_deviation_z': 1.1, 'trade_burst_score': 0.5, 'liquidation_spike_score': 0.0, 'orderbook_imbalance': 0.1, 'realized_vol_pct': 0.006},
    }


def test_reevaluate_strategy_row_applies_parameter_overrides_for_trend():
    row = make_row()
    default_plan = reevaluate_strategy_row(row=row, strategy='trend', parameter_overrides={})
    strict_plan = reevaluate_strategy_row(row=row, strategy='trend', parameter_overrides={'trend_follow_through_enter_min': 5.0})
    assert default_plan.action in {'enter', 'arm', 'watch'}
    assert strict_plan.action in {'arm', 'watch'}


def test_reevaluate_strategy_row_applies_parameter_overrides_for_compression():
    row = make_row() | {
        'bg_regime': 'compression',
        'primary_regime': 'compression',
        'final_regime': 'compression',
        'route_account': 'compression',
        'route_strategy_family': 'compression',
        'primary_features': {
            'adx': 18.0,
            'vwap_deviation_z': 1.0,
            'bollinger_bandwidth_pct': 0.01,
            'realized_vol_pct': 0.004,
            'funding_pctile': 0.5,
            'oi_accel': 0.0,
            'basis_deviation_pct': 0.0,
        },
        'override_features': {
            'vwap_deviation_z': 1.2,
            'trade_burst_score': 0.6,
            'liquidation_spike_score': 0.0,
            'orderbook_imbalance': 0.0,
            'realized_vol_pct': 0.005,
        },
    }
    default_plan = reevaluate_strategy_row(row=row, strategy='compression', parameter_overrides={})
    strict_plan = reevaluate_strategy_row(row=row, strategy='compression', parameter_overrides={'compression_launch_bias_enter_min': 5.0})
    assert default_plan.action in {'enter', 'arm', 'watch'}
    assert strict_plan.action in {'arm', 'watch'}

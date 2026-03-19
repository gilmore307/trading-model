from src.research.runtime_adapters import regime_local_artifact_to_snapshot_row


def test_regime_local_artifact_adapter_produces_snapshot_row():
    row = {
        'artifact_type': 'regime_local_cycle',
        'recorded_at': '2026-03-19T07:24:53.831298+00:00',
        'symbol': 'BTC-USDT-SWAP',
        'final_regime': 'trend',
        'final_confidence': 1.0,
        'background_regime': 'trend',
        'primary_regime': 'trend',
        'override_regime': None,
        'route_strategy_family': 'trend',
        'route_account': 'trend',
        'route_trade_enabled': True,
        'feature_snapshot': {
            'background_4h': {'regime': 'trend', 'confidence': 1.0, 'scores': {'trend': 1.0}, 'tradable': True, 'adx': 48.0, 'ema20_slope': -1.0, 'ema50_slope': -0.5},
            'primary_15m': {'regime': 'trend', 'confidence': 0.9, 'scores': {'trend': 0.9}, 'tradable': True, 'adx': 80.0, 'vwap_deviation_z': -2.0, 'bollinger_bandwidth_pct': 0.02, 'realized_vol_pct': 0.5, 'funding_pctile': 0.6, 'oi_accel': -0.2, 'basis_deviation_pct': -0.001},
            'override_1m': {'regime': None, 'confidence': None, 'scores': None, 'tradable': None, 'vwap_deviation_z': -2.0, 'trade_burst_score': 0.0, 'liquidation_spike_score': 0.0, 'orderbook_imbalance': None, 'realized_vol_pct': 0.6},
        },
    }
    adapted = regime_local_artifact_to_snapshot_row(row)
    assert adapted['timestamp'] == row['recorded_at']
    assert adapted['background_4h']['primary'] == 'trend'
    assert adapted['primary_15m']['primary'] == 'trend'
    assert adapted['final_decision']['primary'] == 'trend'
    assert adapted['route_decision']['account'] == 'trend'

from src.runner.test_mode import _cleanup_test_state


def test_cleanup_test_state_resets_positions_and_bucket():
    snapshot = {
        'positions': {
            'test:breakout:XRP-USDT-SWAP': [{'status': 'open'}],
        },
        'buckets': {
            'test:breakout:XRP-USDT-SWAP': {
                'initial_capital_usdt': 500.0,
                'available_usdt': 20.0,
                'allocated_usdt': 480.0,
                'locked': True,
                'lock_reason': 'test',
            },
        },
        'last_signals': {},
    }
    updated = _cleanup_test_state(snapshot, 'breakout', ['XRP-USDT-SWAP'])
    assert updated['positions']['test:breakout:XRP-USDT-SWAP'] == []
    assert updated['buckets']['test:breakout:XRP-USDT-SWAP']['available_usdt'] == 500.0
    assert updated['buckets']['test:breakout:XRP-USDT-SWAP']['allocated_usdt'] == 0.0
    assert updated['buckets']['test:breakout:XRP-USDT-SWAP']['locked'] is False
    assert updated['open_positions'] == 0

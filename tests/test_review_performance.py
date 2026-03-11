from src.review.performance import build_performance_snapshot


def test_build_performance_snapshot_expands_known_accounts():
    snapshot = build_performance_snapshot(
        {
            'trend': {'pnl_usdt': 12.5, 'trade_count': 3, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 7.0, 'fee_usdt': 0.4, 'source': 'simulated'},
        }
    )
    accounts = {row['account']: row for row in snapshot['accounts']}
    assert accounts['trend']['pnl_usdt'] == 12.5
    assert accounts['trend']['trade_count'] == 3
    assert accounts['router_composite']['fee_usdt'] == 0.4
    assert snapshot['status'] == 'ready'
    assert 'pnl_available:trend' in snapshot['highlights']


def test_build_performance_snapshot_defaults_to_pending_data():
    snapshot = build_performance_snapshot()
    assert snapshot['status'] == 'pending_data'
    assert len(snapshot['accounts']) == 7

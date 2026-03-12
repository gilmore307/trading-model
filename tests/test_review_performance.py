from src.review.performance import build_performance_snapshot


def test_build_performance_snapshot_expands_known_accounts():
    snapshot = build_performance_snapshot(
        {
            'trend': {'realized_pnl_usdt': 10.0, 'unrealized_pnl_usdt': 2.5, 'trade_count': 3, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 7.0, 'fee_usdt': 0.4, 'source': 'simulated'},
        }
    )
    accounts = {row['account']: row for row in snapshot['accounts']}
    assert accounts['trend']['pnl_usdt'] == 12.5
    assert accounts['trend']['realized_pnl_usdt'] == 10.0
    assert accounts['trend']['unrealized_pnl_usdt'] == 2.5
    assert accounts['trend']['unrealized_pnl_start_usdt'] is None
    assert accounts['trend']['unrealized_pnl_change_usdt'] is None
    assert accounts['trend']['trade_count'] == 3
    assert accounts['router_composite']['fee_usdt'] == 0.4
    assert snapshot['status'] == 'ready'
    assert 'pnl_available:trend' in snapshot['highlights']


def test_build_performance_snapshot_defaults_to_pending_data():
    snapshot = build_performance_snapshot()
    assert snapshot['status'] == 'pending_data'
    assert len(snapshot['accounts']) == 7


def test_build_performance_snapshot_exposes_extended_fields_and_highlights():
    snapshot = build_performance_snapshot(
        {
            'trend': {
                'realized_pnl_usdt': 8.0,
                'unrealized_pnl_usdt': 2.0,
                'unrealized_pnl_start_usdt': 1.0,
                'unrealized_pnl_change_usdt': 1.0,
                'pnl_usdt': 10.0,
                'equity_start_usdt': 1000.0,
                'equity_end_usdt': 1010.0,
                'equity_change_usdt': 10.0,
                'funding_usdt': -0.2,
                'source': 'canonical',
            },
        }
    )
    trend = next(row for row in snapshot['accounts'] if row['account'] == 'trend')
    assert trend['realized_pnl_usdt'] == 8.0
    assert trend['unrealized_pnl_usdt'] == 2.0
    assert trend['unrealized_pnl_start_usdt'] == 1.0
    assert trend['unrealized_pnl_change_usdt'] == 1.0
    assert trend['equity_end_usdt'] == 1010.0
    assert trend['equity_change_usdt'] == 10.0
    assert trend['funding_usdt'] == -0.2
    assert 'equity_available:trend' in snapshot['highlights']
    assert 'funding_available:trend' in snapshot['highlights']

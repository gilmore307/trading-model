from types import SimpleNamespace

from src.review.account_metrics import build_account_metrics_from_cycle


def test_build_account_metrics_from_cycle_merges_receipt_fee_and_balance_summary():
    receipt = SimpleNamespace(
        account='trend',
        raw={
            'account_alias': 'trend',
            'fee_usdt': 0.2,
        },
    )
    metrics = build_account_metrics_from_cycle(
        receipt=receipt,
        balance_summary={
            'account_alias': 'trend',
            'equity_usdt': 1200.0,
            'pnl_usdt': 18.5,
        },
    )
    assert metrics['trend']['fee_usdt'] == 0.2
    assert metrics['trend']['equity_usdt'] == 1200.0
    assert metrics['trend']['pnl_usdt'] == 18.5


def test_build_account_metrics_from_cycle_keeps_extended_canonical_fields():
    receipt = SimpleNamespace(
        account='trend',
        raw={
            'account_alias': 'trend',
            'fee_usdt': 0.2,
            'funding_usdt': -0.1,
            'realized_pnl_usdt': 6.0,
        },
    )
    metrics = build_account_metrics_from_cycle(
        receipt=receipt,
        balance_summary={
            'account_alias': 'trend',
            'equity_usdt': 1200.0,
            'pnl_usdt': 18.5,
        },
    )
    assert metrics['trend']['funding_usdt'] == -0.1
    assert metrics['trend']['realized_pnl_usdt'] == 6.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 18.5
    assert metrics['trend']['equity_end_usdt'] == 1200.0

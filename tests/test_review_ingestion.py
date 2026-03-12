from src.review.ingestion import canonicalize_history_row


def test_canonicalize_history_row_prefers_receipt_and_collects_summary_metrics():
    row = {
        'receipt': {
            'account': 'trend',
            'raw': {
                'account_alias': 'trend',
                'fee_usdt': 0.12,
            },
        },
        'summary': {
            'account_metrics': {
                'trend': {
                    'pnl_usdt': 10.0,
                    'equity_usdt': 1005.0,
                },
                'router_composite': {
                    'fee_usdt': 0.33,
                },
            }
        },
    }
    metrics = canonicalize_history_row(row)
    assert metrics['trend']['fee_usdt'] == 0.12
    assert metrics['trend']['pnl_usdt'] == 10.0
    assert metrics['trend']['equity_usdt'] == 1005.0
    assert metrics['router_composite']['fee_usdt'] == 0.33


def test_canonicalize_history_row_extracts_extended_performance_fields():
    row = {
        'receipt': {
            'account': 'trend',
            'raw': {
                'account_alias': 'trend',
                'fee_usdt': 0.2,
                'funding_usdt': -0.05,
                'funding_total_usdt': -0.75,
                'realized_pnl_usdt': 4.0,
                'unrealized_pnl_usdt': 1.5,
                'equity_end_usdt': 1006.5,
                'equity_start_usdt': 1001.0,
            },
        },
    }
    metrics = canonicalize_history_row(row)
    assert metrics['trend']['fee_usdt'] == 0.2
    assert metrics['trend']['funding_usdt'] == -0.05
    assert metrics['trend']['funding_total_usdt'] == -0.75
    assert metrics['trend']['realized_pnl_usdt'] == 4.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 1.5
    assert metrics['trend']['pnl_usdt'] == 5.5
    assert metrics['trend']['equity_end_usdt'] == 1006.5
    assert metrics['trend']['equity_change_usdt'] == 5.5

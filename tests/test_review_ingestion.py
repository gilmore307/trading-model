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

from src.review.report import _build_execution_quality_summary


def test_execution_quality_summary_includes_confirmation_breakdown():
    rows = [
        {
            'summary': {
                'strategy_stats_eligible': True,
                'strategy_stats_reason': 'clean_execution',
            },
            'verification_snapshot': {
                'local_position_reason': 'exchange_position_trade_confirmed',
            },
        },
        {
            'summary': {
                'strategy_stats_eligible': True,
                'strategy_stats_reason': 'clean_execution',
            },
            'verification_snapshot': {
                'local_position_reason': 'exchange_position_trade_ids_confirmed',
            },
        },
        {
            'summary': {
                'strategy_stats_eligible': True,
                'strategy_stats_reason': 'clean_execution',
            },
            'verification_snapshot': {
                'local_position_reason': 'exchange_position_confirmed',
            },
        },
        {
            'summary': {
                'strategy_stats_eligible': False,
                'strategy_stats_reason': 'forced_exit_recovery',
                'entry_verified_hint': True,
                'entry_trade_confirmed': True,
                'account_metrics': {},
            },
            'verification_snapshot': {
                'local_position_reason': 'exit_verification_timeout',
            },
        },
    ]

    summary = _build_execution_quality_summary(rows)
    breakdown = {row['mode']: row['count'] for row in summary['confirmation_breakdown']}
    assert summary['clean_trade_count'] == 3
    assert summary['excluded_trade_count'] == 1
    assert breakdown['trade_confirmed'] == 1
    assert breakdown['trade_ids_confirmed'] == 1
    assert breakdown['position_confirmed'] == 1
    assert summary['excluded_samples'][0]['entry_verified_hint'] is True
    assert summary['excluded_samples'][0]['entry_trade_confirmed'] is True

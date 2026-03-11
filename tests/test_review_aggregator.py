import json
from pathlib import Path

from src.review.aggregator import aggregate_from_execution_history


def test_aggregate_from_execution_history_counts_actions_and_exposure(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'composite_position_owner': 'trend',
                'composite_plan_action': 'enter',
            },
            'compare_snapshot': {
                'accounts': [
                    {'account': 'trend', 'has_position': True},
                    {'account': 'meanrev', 'has_position': False},
                ]
            },
        },
        {
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': None,
                'composite_position_owner': 'trend',
                'composite_plan_action': 'hold',
            },
            'compare_snapshot': {
                'accounts': [
                    {'account': 'trend', 'has_position': True},
                    {'account': 'meanrev', 'has_position': False},
                ]
            },
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['trade_count'] == 1
    assert metrics['trend']['exposure_time_pct'] == 100.0
    assert metrics['meanrev']['trade_count'] == 0
    assert metrics['flat_compare']['trade_count'] == 0


def test_aggregate_from_execution_history_ingests_receipt_fee_and_summary_performance(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {'pnl_usdt': 15.5, 'equity_usdt': 1020.0},
                },
            },
            'receipt': {
                'account': 'trend',
                'raw': {'account_alias': 'trend', 'fee_usdt': 0.25},
            },
            'compare_snapshot': {
                'accounts': [
                    {'account': 'trend', 'has_position': True},
                ]
            },
        }
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['trade_count'] == 1
    assert metrics['trend']['fee_usdt'] == 0.25
    assert metrics['trend']['pnl_usdt'] == 15.5
    assert metrics['trend']['equity_usdt'] == 1020.0

import json
from datetime import UTC, datetime
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
                    'trend': {'pnl_usdt': 15.5, 'equity_end_usdt': 1020.0},
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
    assert metrics['trend']['equity_end_usdt'] == 1020.0
    assert metrics['trend']['equity_usdt'] == 1020.0


def test_aggregate_from_execution_history_tracks_extended_canonical_performance(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 5.0,
                        'unrealized_pnl_usdt': 1.0,
                        'pnl_usdt': 6.0,
                        'equity_end_usdt': 1005.0,
                        'funding_usdt': -0.1,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 7.0,
                        'unrealized_pnl_usdt': 2.0,
                        'pnl_usdt': 9.0,
                        'equity_end_usdt': 1009.0,
                        'funding_usdt': -0.15,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['realized_pnl_usdt'] == 7.0
    assert metrics['trend']['unrealized_pnl_start_usdt'] == 1.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 2.0
    assert metrics['trend']['unrealized_pnl_change_usdt'] == 1.0
    assert metrics['trend']['pnl_usdt'] == 9.0
    assert metrics['trend']['equity_start_usdt'] == 1005.0
    assert metrics['trend']['equity_end_usdt'] == 1009.0
    assert metrics['trend']['equity_change_usdt'] == 4.0
    assert metrics['trend']['funding_usdt'] == -0.25



def test_aggregate_from_execution_history_inferrs_window_realized_from_equity_and_unrealized_boundaries(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'unrealized_pnl_usdt': 4.0,
                        'equity_start_usdt': 1000.0,
                        'equity_end_usdt': 1012.0,
                        'funding_total_usdt': -1.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-10T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'unrealized_pnl_usdt': 6.0,
                        'equity_end_usdt': 1017.0,
                        'funding_total_usdt': -2.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['equity_change_usdt'] == 17.0
    assert metrics['trend']['funding_usdt'] == -1.0
    assert metrics['trend']['unrealized_pnl_start_usdt'] == 4.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 6.0
    assert metrics['trend']['unrealized_pnl_change_usdt'] == 2.0
    assert metrics['trend']['realized_pnl_usdt'] == 16.0


def test_aggregate_from_execution_history_prefers_cumulative_funding_snapshots(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'funding_usdt': -0.10,
                        'funding_total_usdt': -1.50,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-10T12:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'funding_usdt': -0.20,
                        'funding_total_usdt': -1.90,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['funding_start_total_usdt'] == -1.5
    assert metrics['trend']['funding_total_usdt'] == -1.9
    assert metrics['trend']['funding_usdt'] == -0.4


def test_aggregate_from_execution_history_prefers_explicit_equity_start_semantics(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 2.0,
                        'unrealized_pnl_usdt': 1.0,
                        'pnl_usdt': 3.0,
                        'equity_start_usdt': 1000.0,
                        'equity_end_usdt': 1003.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-10T12:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 4.0,
                        'unrealized_pnl_usdt': 2.0,
                        'pnl_usdt': 6.0,
                        'equity_start_usdt': 1004.0,
                        'equity_end_usdt': 1006.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['equity_start_usdt'] == 1000.0
    assert metrics['trend']['equity_end_usdt'] == 1006.0
    assert metrics['trend']['equity_change_usdt'] == 6.0


def test_aggregate_from_execution_history_computes_window_drawdown_from_equity_path(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'equity_start_usdt': 1000.0,
                        'equity_end_usdt': 1050.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-09T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'equity_end_usdt': 990.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-10T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'equity_end_usdt': 1010.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['equity_start_usdt'] == 1000.0
    assert metrics['trend']['equity_end_usdt'] == 1010.0
    assert metrics['trend']['max_drawdown_pct'] == 5.714286


def test_aggregate_from_execution_history_respects_review_window_and_timestamp_order(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-07T23:59:59+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'pnl_usdt': 1.0,
                        'equity_end_usdt': 999.0,
                        'funding_usdt': -0.05,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': False}]},
        },
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 2.0,
                        'unrealized_pnl_usdt': 1.0,
                        'pnl_usdt': 3.0,
                        'equity_end_usdt': 1003.0,
                        'funding_usdt': -0.10,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-10T12:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 4.0,
                        'unrealized_pnl_usdt': 2.0,
                        'pnl_usdt': 6.0,
                        'equity_end_usdt': 1006.0,
                        'funding_usdt': -0.20,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-15T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'exit',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 8.0,
                        'unrealized_pnl_usdt': 0.0,
                        'pnl_usdt': 8.0,
                        'equity_end_usdt': 1008.0,
                        'funding_usdt': -0.30,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': False}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(
        history,
        window_start=datetime(2026, 3, 8, 0, 0, tzinfo=UTC),
        window_end=datetime(2026, 3, 15, 0, 0, tzinfo=UTC),
    )
    assert metrics['trend']['trade_count'] == 1
    assert metrics['trend']['exposure_time_pct'] == 100.0
    assert metrics['trend']['realized_pnl_usdt'] == 4.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 2.0
    assert metrics['trend']['pnl_usdt'] == 6.0
    assert metrics['trend']['equity_start_usdt'] == 1003.0
    assert metrics['trend']['equity_end_usdt'] == 1006.0
    assert metrics['trend']['equity_change_usdt'] == 3.0
    assert metrics['trend']['funding_usdt'] == -0.30


def test_aggregate_from_execution_history_sorts_out_of_order_rows_by_timestamp(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-10T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 8.0,
                        'unrealized_pnl_usdt': 1.0,
                        'pnl_usdt': 9.0,
                        'equity_end_usdt': 990.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 2.0,
                        'unrealized_pnl_usdt': 1.0,
                        'pnl_usdt': 3.0,
                        'equity_start_usdt': 1000.0,
                        'equity_end_usdt': 1050.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-09T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {
                    'trend': {
                        'realized_pnl_usdt': 4.0,
                        'unrealized_pnl_usdt': 2.0,
                        'pnl_usdt': 6.0,
                        'equity_end_usdt': 1010.0,
                        'max_drawdown_pct': 1.0,
                    },
                },
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    metrics = aggregate_from_execution_history(history)
    assert metrics['trend']['realized_pnl_usdt'] == 8.0
    assert metrics['trend']['unrealized_pnl_usdt'] == 1.0
    assert metrics['trend']['pnl_usdt'] == 9.0
    assert metrics['trend']['equity_start_usdt'] == 1000.0
    assert metrics['trend']['equity_end_usdt'] == 990.0
    assert metrics['trend']['equity_change_usdt'] == -10.0
    assert metrics['trend']['max_drawdown_pct'] == 5.714286

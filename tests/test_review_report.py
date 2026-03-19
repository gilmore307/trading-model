from datetime import UTC, datetime

import json
from pathlib import Path

from src.review.framework import build_monthly_window, build_quarterly_window, build_weekly_window
from src.review.report import build_report_scaffold


def test_weekly_report_scaffold_includes_compare_sections():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    compare_snapshot = {
        'accounts': [{'account': 'trend', 'label': 'Trend'}],
        'highlights': ['router_selected:trend'],
    }
    metrics_by_account = {
        'trend': {'realized_pnl_usdt': 10.0, 'unrealized_pnl_usdt': 2.5, 'trade_count': 3, 'source': 'demo'},
    }
    report = build_report_scaffold(window, compare_snapshot, metrics_by_account)
    section_keys = [section['key'] for section in report['sections']]
    assert 'account_comparison' in section_keys
    assert 'router_composite_review' in section_keys
    assert report['compare_snapshot']['highlights'] == ['router_selected:trend']
    assert report['metrics']['performance']['status'] == 'ready'
    trend_row = next(row for row in report['metrics']['performance']['accounts'] if row['account'] == 'trend')
    assert trend_row['pnl_usdt'] == 12.5
    assert report['parameter_candidates']['auto_candidate_params']


def test_report_scaffold_can_aggregate_from_history(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    history.write_text(json.dumps({
        'summary': {'plan_account': 'trend', 'plan_action': 'enter', 'receipt_accepted': True, 'strategy_stats_eligible': True, 'strategy_stats_reason': 'clean_execution', 'composite_position_owner': 'trend', 'composite_plan_action': 'enter'},
        'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]}
    }) + '\n', encoding='utf-8')
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(window, history_path=str(history))
    trend_row = next(row for row in report['metrics']['performance']['accounts'] if row['account'] == 'trend')
    assert trend_row['trade_count'] == 1
    assert trend_row['exposure_time_pct'] == 100.0
    assert report['metrics']['execution_quality']['clean_trade_count'] == 1


def test_report_scaffold_filters_history_to_review_window(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'observed_at': '2026-03-07T23:59:59+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'account_metrics': {'trend': {'pnl_usdt': 1.0, 'equity_end_usdt': 999.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': False}]},
        },
        {
            'observed_at': '2026-03-08T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'enter',
                'receipt_accepted': True,
                'account_metrics': {'trend': {'pnl_usdt': 3.0, 'equity_end_usdt': 1003.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-14T23:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'hold',
                'receipt_accepted': True,
                'account_metrics': {'trend': {'pnl_usdt': 6.0, 'equity_end_usdt': 1006.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'observed_at': '2026-03-15T00:00:00+00:00',
            'summary': {
                'plan_account': 'trend',
                'plan_action': 'exit',
                'receipt_accepted': True,
                'account_metrics': {'trend': {'pnl_usdt': 8.0, 'equity_end_usdt': 1008.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': False}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(window, history_path=str(history))
    trend_row = next(row for row in report['metrics']['performance']['accounts'] if row['account'] == 'trend')
    assert trend_row['trade_count'] == 1
    assert trend_row['pnl_usdt'] == 6.0
    assert trend_row['equity_start_usdt'] == 1003.0
    assert trend_row['equity_end_usdt'] == 1006.0
    assert trend_row['equity_change_usdt'] == 3.0


def test_quarterly_report_scaffold_includes_structural_review_section():
    window = build_quarterly_window(
        datetime(2026, 1, 4, 0, 0, tzinfo=UTC),
        datetime(2026, 4, 5, 0, 0, tzinfo=UTC),
    )
    report = build_report_scaffold(window)
    section_keys = [section['key'] for section in report['sections']]
    assert 'structural_review' in section_keys
    assert report['parameter_candidates']['structural_params']


def test_report_scaffold_builds_readable_performance_summary():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.5, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'meanrev': {'pnl_usdt': 5.0, 'fee_usdt': 0.2, 'equity_change_usdt': 5.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 9.0, 'fee_usdt': 0.3, 'equity_change_usdt': 9.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 1.0, 'fee_usdt': 0.0, 'equity_change_usdt': 1.0, 'source': 'baseline'},
        },
    )
    summary = report['metrics']['performance_summary']
    assert summary['top_account']['account'] == 'trend'
    assert summary['highest_fee_drag_account']['account'] == 'trend'
    assert summary['router_vs_best_strategy']['best_strategy_account'] == 'trend'
    assert summary['router_vs_flat_compare']['flat_compare_account'] == 'flat_compare'
    assert 'top_account:trend' in summary['insights']


def test_report_scaffold_populates_operator_facing_sections():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    compare_snapshot = {
        'accounts': [{'account': 'trend', 'label': 'Trend', 'has_position': True}],
        'highlights': ['router_selected:trend', 'composite_owner:trend'],
    }
    report = build_report_scaffold(
        window,
        compare_snapshot=compare_snapshot,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.5, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 9.0, 'fee_usdt': 0.3, 'equity_change_usdt': 9.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 1.0, 'fee_usdt': 0.0, 'equity_change_usdt': 1.0, 'source': 'baseline'},
        },
    )
    sections = {section['key']: section for section in report['sections']}
    assert sections['account_comparison']['status'] == 'ready'
    assert sections['account_comparison']['items'][0]['kind'] == 'leaderboard'
    assert sections['router_composite_review']['status'] == 'ready'
    assert sections['router_composite_review']['items'][0]['kind'] == 'router_vs_best_strategy'
    assert 'router_selected:trend' in sections['router_composite_review']['highlights']


def test_report_scaffold_populates_parameter_candidates_from_performance_signals():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.6, 'trade_count': 6, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'meanrev': {'pnl_usdt': -2.0, 'fee_usdt': 0.1, 'trade_count': 7, 'equity_change_usdt': -2.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 1.0, 'fee_usdt': 0.2, 'equity_change_usdt': 1.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 3.0, 'fee_usdt': 0.0, 'equity_change_usdt': 3.0, 'source': 'baseline'},
        },
    )
    parameter_section = next(section for section in report['sections'] if section['key'] == 'parameter_review')
    candidate_names = [item['name'] for item in parameter_section['items'] if item.get('kind') == 'candidate']
    assert 'fee_burden_frequency_gate' in candidate_names
    assert 'cooldown_seconds' in candidate_names
    assert 'entry_threshold' in candidate_names


def test_report_scaffold_adds_high_exposure_candidate_signal():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 4.0, 'fee_usdt': 0.1, 'equity_change_usdt': 4.0, 'exposure_time_pct': 85.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 2.0, 'fee_usdt': 0.0, 'equity_change_usdt': 2.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 1.0, 'fee_usdt': 0.0, 'equity_change_usdt': 1.0, 'source': 'baseline'},
        },
    )
    parameter_section = next(section for section in report['sections'] if section['key'] == 'parameter_review')
    confidence_rows = [item for item in parameter_section['items'] if item.get('name') == 'confidence_gate']
    assert confidence_rows
    assert confidence_rows[0]['target_account'] == 'trend'


def test_monthly_report_marks_router_switch_gating_discuss_first_when_router_underperforms():
    window = build_monthly_window(
        datetime(2026, 2, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
    )
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 10.0, 'fee_usdt': 0.1, 'equity_change_usdt': 10.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 2.0, 'fee_usdt': 0.2, 'equity_change_usdt': 2.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 1.0, 'fee_usdt': 0.0, 'equity_change_usdt': 1.0, 'source': 'baseline'},
        },
    )
    parameter_section = next(section for section in report['sections'] if section['key'] == 'parameter_review')
    router_rows = [item for item in parameter_section['items'] if item.get('name') == 'router_switch_gating']
    assert router_rows
    assert router_rows[0]['status'] == 'discuss_first'
    seeded_discuss = {row['name']: row['status'] for row in parameter_section['seeded_discuss_first']}
    assert seeded_discuss['router_switch_gating'] == 'discuss_first'


def test_report_scaffold_builds_executive_summary_and_actions():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 12.0, 'fee_usdt': 0.6, 'trade_count': 6, 'equity_change_usdt': 12.0, 'source': 'demo'},
            'meanrev': {'pnl_usdt': -2.0, 'fee_usdt': 0.1, 'trade_count': 7, 'equity_change_usdt': -2.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 1.0, 'fee_usdt': 0.2, 'equity_change_usdt': 1.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 3.0, 'fee_usdt': 0.0, 'equity_change_usdt': 3.0, 'source': 'baseline'},
        },
    )
    assert report['executive_summary']['status'] == 'ready'
    assert any('Top account:' in line for line in report['executive_summary']['bullets'])
    assert report['recommended_actions']
    assert any(action['title'] == 'Review fee_burden_frequency_gate' for action in report['recommended_actions'])
    assert report['narrative_blocks']
    assert report['narrative_blocks'][0]['key'] == 'executive_summary'


def test_report_scaffold_surfaces_execution_quality_dual_ledger(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'summary': {
                'regime': 'trend',
                'route_strategy_family': 'trend',
                'plan_account': 'trend', 'plan_action': 'enter', 'receipt_accepted': True,
                'strategy_stats_eligible': True, 'strategy_stats_reason': 'clean_execution',
                'account_metrics': {'trend': {'pnl_usdt': 5.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': True}]},
        },
        {
            'summary': {
                'regime': 'trend',
                'route_strategy_family': 'trend',
                'plan_account': 'trend', 'plan_action': 'exit', 'receipt_accepted': True,
                'strategy_stats_eligible': False, 'strategy_stats_reason': 'forced_exit_recovery',
                'account_metrics': {'trend': {'pnl_usdt': -2.5}},
            },
            'compare_snapshot': {'accounts': [{'account': 'trend', 'has_position': False}]},
        },
        {
            'summary': {
                'regime': 'crowded',
                'route_strategy_family': 'crowded',
                'plan_account': 'meanrev', 'plan_action': 'enter', 'receipt_accepted': True,
                'strategy_stats_eligible': False, 'strategy_stats_reason': 'missed_entry',
                'account_metrics': {'meanrev': {'pnl_usdt': 0.0}},
            },
            'compare_snapshot': {'accounts': [{'account': 'meanrev', 'has_position': False}]},
        },
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(window, history_path=str(history))
    eq = report['metrics']['execution_quality']
    assert eq['clean_trade_count'] == 1
    assert eq['excluded_trade_count'] == 2
    assert eq['excluded_pnl_usdt'] == -2.5
    section = next(section for section in report['sections'] if section['key'] == 'execution_quality')
    assert section['status'] == 'ready'
    assert any(row['reason'] == 'forced_exit_recovery' for row in eq['top_excluded_reasons'])
    assert any(row['reason'] == 'missed_entry' for row in eq['top_excluded_reasons'])
    breakdown = {row['reason']: row for row in eq['anomaly_breakdown']}
    assert breakdown['forced_exit_recovery']['count'] == 1
    assert breakdown['forced_exit_recovery']['pnl_usdt'] == -2.5
    assert breakdown['missed_entry']['count'] == 1
    assert breakdown['missed_entry']['accounts'] == ['meanrev']
    regime_rows = {row['regime']: row for row in report['metrics']['regime_local']['rows']}
    assert regime_rows['trend']['clean_cycles'] == 1
    assert regime_rows['trend']['excluded_cycles'] == 1
    assert regime_rows['trend']['dominant_route_family'] == 'trend'
    assert regime_rows['crowded']['excluded_cycles'] == 1
    mapping_rows = {row['regime']: row for row in report['metrics']['mapping_validity']['rows']}
    assert mapping_rows['trend']['expected_account'] == 'trend'
    assert mapping_rows['trend']['dominant_route'] == 'trend'
    assert mapping_rows['trend']['matched_cycles'] == 2
    assert mapping_rows['crowded']['expected_account'] == 'crowded'
    assert mapping_rows['crowded']['dominant_route'] == 'meanrev'
    assert mapping_rows['crowded']['matched_cycles'] == 0

from datetime import UTC, datetime

import json
from pathlib import Path

from src.review.framework import build_monthly_window, build_quarterly_window, build_weekly_window
from src.review.report import build_report_scaffold


def test_report_scaffold_surfaces_attribution_confidence():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {
                'pnl_usdt': 12.5,
                'fee_usdt': 0.2,
                'trade_count': 2,
                'attribution_fee_source': 'fill_aggregation',
                'attribution_realized_pnl_source': 'fill_aggregation',
                'attribution_equity_source': 'balance_summary',
                'source': 'demo',
            },
        },
    )
    trend_row = next(row for row in report['metrics']['performance']['accounts'] if row['account'] == 'trend')
    assert trend_row['attribution_confidence'] == 'high'
    assert trend_row['attribution_fee_source'] == 'fill_aggregation'
    assert 'high_confidence_attribution:trend' in report['metrics']['performance_summary']['insights']


def test_weekly_report_scaffold_includes_live_review_sections():
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
    assert 'live_performance_summary' in section_keys
    assert 'execution_deviation_review' in section_keys
    assert report['compare_snapshot']['highlights'] == ['router_selected:trend']
    assert report['metrics']['performance']['status'] == 'ready'
    trend_row = next(row for row in report['metrics']['performance']['accounts'] if row['account'] == 'trend')
    assert trend_row['pnl_usdt'] == 12.5
    assert report['parameter_candidates']['auto_candidate_params'] == []


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
    assert report['parameter_candidates']['structural_params'] == []


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
    assert sections['live_performance_summary']['status'] == 'ready'
    assert sections['live_performance_summary']['items'][0]['kind'] == 'leaderboard'
    assert sections['execution_deviation_review']['status'] == 'ready'
    assert sections['execution_deviation_review']['items'][0]['kind'] == 'router_vs_best_strategy'
    assert 'router_selected:trend' in sections['execution_deviation_review']['highlights']


def test_report_scaffold_populates_execution_improvement_items_from_performance_signals():
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
    section = next(section for section in report['sections'] if section['key'] == 'execution_improvement_review')
    item_names = [item['name'] for item in section['items'] if item.get('kind') == 'improvement']
    assert 'trade_frequency_review' in item_names
    assert 'order_timing_and_cooldown_review' in item_names
    assert 'negative_live_pnl_review' in item_names


def test_report_scaffold_adds_high_exposure_execution_signal():
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(
        window,
        metrics_by_account={
            'trend': {'pnl_usdt': 4.0, 'fee_usdt': 0.1, 'equity_change_usdt': 4.0, 'exposure_time_pct': 85.0, 'source': 'demo'},
            'router_composite': {'pnl_usdt': 2.0, 'fee_usdt': 0.0, 'equity_change_usdt': 2.0, 'source': 'simulated'},
            'flat_compare': {'pnl_usdt': 1.0, 'fee_usdt': 0.0, 'equity_change_usdt': 1.0, 'source': 'baseline'},
        },
    )
    section = next(section for section in report['sections'] if section['key'] == 'execution_improvement_review')
    rows = [item for item in section['items'] if item.get('name') == 'position_drift_review']
    assert rows
    assert rows[0]['target_account'] == 'trend'


def test_monthly_report_marks_strategy_upgrade_calibrate_check_when_router_underperforms():
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
    section = next(section for section in report['sections'] if section['key'] == 'execution_improvement_review')
    router_rows = [item for item in section['items'] if item.get('name') == 'strategy_upgrade_calibrate_check']
    assert router_rows
    assert router_rows[0]['status'] == 'upgrade_event_only'


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
    assert any(action['title'] == 'Review trade_frequency_review' for action in report['recommended_actions'])
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


def test_report_scaffold_surfaces_overlap_review_from_score_vectors(tmp_path: Path):
    history = tmp_path / 'execution-cycles.jsonl'
    rows = [
        {
            'final_regime': 'trend',
            'feature_snapshot': {
                'primary_15m': {
                    'scores': {
                        'trend': 0.71,
                        'range': 0.24,
                        'compression': 0.12,
                        'crowded': 0.64,
                        'shock': 0.10,
                    }
                }
            },
            'shadow_plans': {
                'trend': {'action': 'enter', 'account': 'trend', 'reason': 'trend_follow_through_confirmed'},
                'range': {'action': 'watch', 'account': None, 'reason': 'range_requires_reversion_confirmation'},
                'compression': {'action': 'watch', 'account': None, 'reason': 'compression_bias_insufficient'},
                'crowded': {'action': 'arm', 'account': 'crowded', 'reason': 'crowded_reversal_setup_forming'},
                'shock': {'action': 'watch', 'account': None, 'reason': 'shock_event_score_low'},
            },
            'summary': {
                'regime': 'trend',
                'route_strategy_family': 'trend',
                'plan_account': 'trend',
                'strategy_stats_eligible': True,
                'account_metrics': {'trend': {'pnl_usdt': 1.0}},
            },
        }
    ]
    history.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    window = build_weekly_window(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    report = build_report_scaffold(window, history_path=str(history))
    overlap_rows = report['metrics']['overlap']['rows']
    assert len(overlap_rows) == 1
    assert overlap_rows[0]['top_regime'] == 'trend'
    assert overlap_rows[0]['runner_up_regime'] == 'crowded'
    assert overlap_rows[0]['score_gap'] == 0.07
    activity_rows = {row['strategy_name']: row for row in report['metrics']['strategy_activity']['rows']}
    assert activity_rows['trend']['enter_count'] == 1
    assert activity_rows['crowded']['arm_count'] == 1
    assert activity_rows['range']['watch_count'] == 1
    assert report['metrics']['strategy_activity']['matrix']['trend']['trend']['enter'] == 1
    assert report['metrics']['strategy_activity']['matrix']['crowded']['trend']['arm'] == 1
    shadow_rows = {row['regime']: row for row in report['metrics']['shadow_decision']['rows']}
    assert shadow_rows['trend']['selected_family'] == 'trend'
    assert shadow_rows['trend']['enter_top'][0]['strategy_name'] == 'trend'
    assert shadow_rows['trend']['arm_top'][0]['strategy_name'] == 'crowded'

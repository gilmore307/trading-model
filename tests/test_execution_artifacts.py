import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.execution.pipeline import ExecutionDecisionTrace, ExecutionCycleResult
from src.execution.adapters import ExecutionReceipt
from src.execution.controller import RouteControlResult
from src.execution.policy import PolicyDecision
from src.reconcile.alignment import AlignmentResult
from src.runners.execution_cycle import build_execution_artifact, persist_execution_artifact, ANOMALY_HISTORY_PATH, REGIME_HISTORY_PATH, STRATEGY_ACTIVITY_PATH
from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import ExecutionPlan


def test_build_execution_artifact_includes_summary_fields():
    regime_output = RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={'adx': 30.0, 'last_price': 100000.0},
        primary_features={'adx': 28.0, 'last_price': 100100.0},
        override_features={'trade_burst_score': 0.7, 'last_price': 100120.0},
        final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
        decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['high_confidence']},
    )
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='trend', account='trend', action='enter', reason='trend_follow_through_confirmed'),
        receipt=ExecutionReceipt(accepted=True, mode='okx_demo', account='trend', symbol='BTC-USDT-SWAP', action='entry', side='long', size=1.0, order_id='ord-1', reason='trend_follow_through_confirmed', observed_at=datetime.now(UTC), raw={'dry_run': True, 'account_alias': 'trend', 'fee_usdt': 0.15, 'realized_pnl_usdt': 3.0, 'equity_usdt': 1500.0, 'pnl_usdt': 25.0}),
        local_position=None,
        verification_position=None,
        reconcile_result=RouteControlResult(
            alignment=AlignmentResult(ok=True, issues=[]),
            policy=PolicyDecision(trade_enabled=True, action='continue', reason='alignment_ok'),
            position=None,
        ),
        decision_trace=ExecutionDecisionTrace(
            mode='develop',
            mode_allows_routing=True,
            decision_trade_enabled=True,
            route_trade_enabled=True,
            pipeline_trade_enabled=True,
            allow_reason='route_to_trend',
            block_reason=None,
            diagnostics=['high_confidence'],
        ),
        runtime_state={'mode': 'develop', 'reason': 'dev', 'updated_at': datetime.now(UTC)},
        route_state={'account': 'trend', 'symbol': 'BTC-USDT-SWAP', 'enabled': True, 'frozen_reason': None, 'updated_at': datetime.now(UTC)},
        live_positions=[],
        router_composite={'account': 'router_composite', 'symbol': 'BTC-USDT-SWAP', 'selected_strategy': 'trend', 'source_regime': 'trend', 'source_confidence': 0.8, 'switch_action': 'adopt_target_plan', 'position_owner': 'trend', 'plan': {'action': 'enter'}, 'notes': ['selected_strategy:trend'], 'position': {'side': 'long'}},
    )

    artifact = build_execution_artifact(result)
    assert artifact['artifact_type'] == 'execution_cycle'
    assert artifact['compare_snapshot']['selected_strategy'] == 'trend'
    assert artifact['feature_snapshot']['background_4h']['adx'] == 30.0
    assert artifact['feature_snapshot']['background_4h']['last_price'] == 100000.0
    assert artifact['feature_snapshot']['primary_15m']['adx'] == 28.0
    assert artifact['feature_snapshot']['primary_15m']['last_price'] == 100100.0
    assert artifact['feature_snapshot']['override_1m']['trade_burst_score'] == 0.7
    assert artifact['feature_snapshot']['override_1m']['last_price'] == 100120.0
    assert 'trend' in artifact['shadow_plans']
    assert 'crowded' in artifact['shadow_plans']
    assert artifact['shadow_plans']['trend']['action'] in {'enter', 'arm', 'watch'}
    assert artifact['summary']['runtime_mode'] == 'develop'
    assert artifact['summary']['regime'] == 'trend'
    assert artifact['summary']['plan_action'] == 'enter'
    assert artifact['summary']['allow_reason'] == 'route_to_trend'
    assert artifact['summary']['route_enabled'] is True
    assert artifact['summary']['live_position_count'] == 0
    assert artifact['summary']['composite_selected_strategy'] == 'trend'
    assert artifact['summary']['composite_position_owner'] == 'trend'
    assert artifact['summary']['composite_plan_action'] == 'enter'
    assert artifact['summary']['composite_position_side'] == 'long'
    assert artifact['summary']['receipt_accepted'] is True
    assert artifact['summary']['alignment_ok'] is True
    assert artifact['summary']['strategy_stats_eligible'] is True
    assert artifact['summary']['strategy_stats_reason'] == 'clean_execution'
    assert artifact['summary']['account_metrics']['trend']['fee_usdt'] == 0.15
    assert artifact['summary']['account_metrics']['trend']['realized_pnl_usdt'] == 3.0
    assert artifact['summary']['account_metrics']['trend']['equity_usdt'] == 1500.0
    assert artifact['summary']['account_metrics']['trend']['equity_end_usdt'] == 1500.0
    assert artifact['summary']['account_metrics']['trend']['unrealized_pnl_usdt'] == 25.0
    assert artifact['summary']['account_metrics']['trend']['pnl_usdt'] == 28.0
    assert artifact['attribution_snapshot']['execution_id'] is None
    assert artifact['summary']['attribution_trade_count'] == 0
    assert artifact['summary']['attribution_fee_source'] == 'order_payload'
    assert artifact['summary']['attribution_realized_pnl_source'] == 'order_payload'
    assert artifact['summary']['attribution_equity_source'] == 'balance_summary'


def test_build_execution_artifact_captures_blocked_reason():
    regime_output = RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'chaotic', 'confidence': 0.2, 'reasons': ['weak_signal'], 'secondary': ['range'], 'tradable': False},
        primary_15m={'primary': 'chaotic', 'confidence': 0.2, 'reasons': ['weak_signal'], 'secondary': ['range'], 'tradable': False},
        override_1m=None,
        background_features={},
        primary_features={},
        override_features={},
        final_decision={'primary': 'chaotic', 'confidence': 0.2, 'reasons': ['weak_signal'], 'secondary': ['range'], 'tradable': False},
        route_decision={'regime': 'chaotic', 'account': None, 'strategy_family': None, 'trade_enabled': False, 'allow_reason': None, 'block_reason': 'no_route_for_regime'},
        decision_summary={'regime': 'chaotic', 'confidence': 0.2, 'tradable': False, 'account': None, 'strategy_family': None, 'trade_enabled': False, 'allow_reason': None, 'block_reason': 'regime_non_tradable', 'reasons': ['weak_signal'], 'secondary': ['range'], 'diagnostics': ['regime_marked_non_tradable', 'low_confidence']},
    )
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='chaotic', account=None, action='hold', reason='regime_non_tradable'),
        receipt=None,
        local_position=None,
        verification_position=None,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(
            mode='trade',
            mode_allows_routing=True,
            decision_trade_enabled=False,
            route_trade_enabled=False,
            pipeline_trade_enabled=False,
            allow_reason=None,
            block_reason='regime_non_tradable',
            diagnostics=['decision_gate_blocked', 'low_confidence'],
        ),
        runtime_state={'mode': 'trade', 'reason': 'manual', 'updated_at': datetime.now(UTC)},
        route_state=None,
        live_positions=[],
        router_composite={'account': 'router_composite', 'symbol': 'BTC-USDT-SWAP', 'selected_strategy': None, 'source_regime': 'chaotic', 'source_confidence': 0.2, 'switch_action': 'hold', 'position_owner': None, 'plan': {'action': 'hold'}, 'notes': ['router_not_actionable'], 'position': None},
    )

    artifact = build_execution_artifact(result)
    assert artifact['summary']['plan_action'] == 'hold'
    assert artifact['summary']['block_reason'] == 'regime_non_tradable'
    assert artifact['summary']['trade_enabled'] is False
    assert artifact['summary']['strategy_stats_eligible'] is False
    assert artifact['summary']['strategy_stats_reason'] == 'receipt_not_accepted'


def test_persist_execution_artifact_writes_anomaly_ledger_for_excluded_execution(tmp_path: Path, monkeypatch):
    from src.state.live_position import LivePosition, LivePositionStatus

    anomaly_path = tmp_path / 'execution-anomalies.jsonl'
    monkeypatch.setattr('src.runners.execution_cycle.ANOMALY_HISTORY_PATH', anomaly_path)
    monkeypatch.setattr('src.runners.execution_cycle.REGIME_HISTORY_PATH', tmp_path / 'regime-local-history.jsonl')
    monkeypatch.setattr('src.runners.execution_cycle.STRATEGY_ACTIVITY_PATH', tmp_path / 'strategy-activity-history.jsonl')
    monkeypatch.setattr('src.runners.execution_cycle.LATEST_PATH', tmp_path / 'latest-execution-cycle.json')
    monkeypatch.setattr('src.runners.execution_cycle.HISTORY_PATH', tmp_path / 'execution-cycles.jsonl')

    regime_output = RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={},
        primary_features={},
        override_features={},
        final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
        decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
    )
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='trend', account='trend', action='exit', reason='forced_exit_recovery'),
        receipt=ExecutionReceipt(accepted=True, mode='okx_demo', account='trend', symbol='BTC-USDT-SWAP', action='exit', side=None, size=None, order_id='x1', reason='forced_exit_recovery', observed_at=datetime.now(UTC), raw={'account_alias': 'trend', 'realized_pnl_usdt': -1.5}),
        local_position=LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.FLAT, side=None, size=0.0, reason='forced_exit_recovery', meta={'strategy_stats_eligible': 'false', 'strategy_stats_reason': 'forced_exit_recovery', 'execution_recovery': 'forced_exit'}),
        verification_position=None,
        reconcile_result=RouteControlResult(alignment=AlignmentResult(ok=True, issues=[]), policy=PolicyDecision(trade_enabled=True, action='continue', reason='alignment_ok'), position=None),
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True, allow_reason='route_to_trend', block_reason=None, diagnostics=[]),
        runtime_state={'mode': 'trade', 'reason': 'auto', 'updated_at': datetime.now(UTC)},
        route_state={'account': 'trend', 'symbol': 'BTC-USDT-SWAP', 'enabled': True, 'frozen_reason': None, 'updated_at': datetime.now(UTC)},
        live_positions=[],
        router_composite={'account': 'router_composite', 'symbol': 'BTC-USDT-SWAP', 'selected_strategy': 'trend', 'source_regime': 'trend', 'source_confidence': 0.8, 'switch_action': 'hold', 'position_owner': None, 'plan': {'action': 'hold'}, 'notes': [], 'position': None},
    )
    persist_execution_artifact(result)
    regime_lines = (tmp_path / 'regime-local-history.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(regime_lines) == 1
    regime_row = json.loads(regime_lines[0])
    assert regime_row['artifact_type'] == 'regime_local_cycle'
    assert regime_row['final_regime'] == 'trend'
    assert regime_row['route_strategy_family'] == 'trend'
    assert regime_row['strategy_stats_eligible'] is False
    assert 'shadow_plans' in regime_row
    assert 'trend' in regime_row['shadow_plans']
    activity_lines = (tmp_path / 'strategy-activity-history.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(activity_lines) == 5
    activity_row = json.loads(activity_lines[0])
    assert activity_row['artifact_type'] == 'strategy_activity'
    assert activity_row['final_regime'] == 'trend'
    lines = anomaly_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 1
    anomaly = json.loads(lines[0])
    assert anomaly['artifact_type'] == 'execution_anomaly'
    assert anomaly['execution_recovery'] == 'forced_exit'
    assert anomaly['strategy_stats_reason'] == 'forced_exit_recovery'
    assert anomaly['account'] == 'trend'

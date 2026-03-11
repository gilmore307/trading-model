import json
from dataclasses import dataclass
from datetime import UTC, datetime

from src.execution.pipeline import ExecutionDecisionTrace, ExecutionCycleResult
from src.execution.adapters import ExecutionReceipt
from src.execution.controller import RouteControlResult
from src.execution.policy import PolicyDecision
from src.reconcile.alignment import AlignmentResult
from src.runners.execution_cycle import build_execution_artifact
from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import ExecutionPlan


def test_build_execution_artifact_includes_summary_fields():
    regime_output = RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={'adx': 30.0},
        primary_features={'adx': 28.0},
        override_features={'trade_burst_score': 0.7},
        final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
        decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['high_confidence']},
    )
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='trend', account='trend', action='enter', reason='trend_follow_through_confirmed'),
        receipt=ExecutionReceipt(accepted=True, mode='dry_run', account='trend', symbol='BTC-USDT-SWAP', action='entry', side='long', size=1.0, order_id='ord-1', reason='trend_follow_through_confirmed', observed_at=datetime.now(UTC), raw={'dry_run': True}),
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
    )

    artifact = build_execution_artifact(result)
    assert artifact['artifact_type'] == 'execution_cycle'
    assert artifact['summary']['runtime_mode'] == 'develop'
    assert artifact['summary']['regime'] == 'trend'
    assert artifact['summary']['plan_action'] == 'enter'
    assert artifact['summary']['allow_reason'] == 'route_to_trend'
    assert artifact['summary']['route_enabled'] is True
    assert artifact['summary']['live_position_count'] == 0
    assert artifact['summary']['receipt_accepted'] is True
    assert artifact['summary']['alignment_ok'] is True


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
    )

    artifact = build_execution_artifact(result)
    assert artifact['summary']['plan_action'] == 'hold'
    assert artifact['summary']['block_reason'] == 'regime_non_tradable'
    assert artifact['summary']['trade_enabled'] is False

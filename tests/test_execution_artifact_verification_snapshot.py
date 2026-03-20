from datetime import UTC, datetime

from src.execution.adapters import ExecutionReceipt
from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace
from src.reconcile.alignment import AlignmentResult
from src.routing.composite import RouterCompositeSimulator
from src.runners.execution_cycle import build_execution_artifact
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.state.live_position import LivePosition, LivePositionStatus
from src.execution.controller import RouteControlResult
from src.execution.policy import PolicyDecision
from src.strategies.executors import ExecutionPlan


def test_execution_artifact_includes_verification_snapshot_fields():
    pos = LivePosition(
        account='trend',
        symbol='BTC-USDT-SWAP',
        route='trend',
        status=LivePositionStatus.OPEN,
        side='short',
        size=12.74,
        meta={
            'last_verification_hint': {
                'verified_entry': True,
                'verification_attempts': [
                    {'attempt': 'initial', 'delay_seconds': 0.0, 'trade_confirmed': True}
                ],
            }
        },
    )
    result = ExecutionCycleResult(
        regime_output=RegimeRunnerOutput(
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
        ),
        plan=ExecutionPlan(regime='trend', account='trend', action='enter', side='short', size=12.74, reason='test'),
        receipt=ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account='trend',
            symbol='BTC-USDT-SWAP',
            action='entry',
            side='short',
            size=12.74,
            order_id='ord-1',
            reason='test',
            observed_at=datetime.now(UTC),
            raw={'fill_count': 1},
            execution_id='exec-1',
            client_order_id='cl-1',
            trade_ids=['t1'],
        ),
        local_position=pos,
        verification_position=pos,
        reconcile_result=RouteControlResult(
            alignment=AlignmentResult(ok=True, issues=[]),
            policy=PolicyDecision(trade_enabled=True, action='allow_trade', reason='alignment_ok'),
            position=pos,
        ),
        decision_trace=ExecutionDecisionTrace(
            mode=RuntimeMode.TRADE.value,
            mode_allows_routing=True,
            decision_trade_enabled=True,
            route_trade_enabled=True,
            pipeline_trade_enabled=True,
            pipeline_entered=True,
            submission_allowed=True,
            submission_attempted=True,
            allow_reason='route_to_trend',
            block_reason=None,
            diagnostics=[],
        ),
        runtime_state={'mode': RuntimeMode.TRADE.value},
        route_state={'enabled': True, 'frozen_reason': None},
        live_positions=[],
        router_composite={'selected_strategy': 'trend', 'position_owner': 'trend', 'plan': {'action': 'enter'}, 'position': {'side': 'short'}},
    )

    artifact = build_execution_artifact(result)
    assert artifact['verification_snapshot']['entry_verified_hint'] is True
    assert artifact['verification_snapshot']['entry_trade_confirmed'] is True
    assert artifact['summary']['entry_verified_hint'] is True
    assert artifact['summary']['entry_trade_confirmed'] is True
    assert artifact['summary']['entry_verification_attempt_count'] == 1

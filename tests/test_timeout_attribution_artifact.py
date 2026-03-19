from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.execution.adapters import ExecutionReceipt
from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace
from src.runners.execution_cycle import build_execution_artifact
from src.runners.regime_runner import RegimeRunnerOutput
from src.state.live_position import LivePosition, LivePositionStatus
from src.strategies.executors import ExecutionPlan


def test_timeout_artifact_preserves_recovery_and_attribution_fields():
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
    local = LivePosition(
        account='trend',
        symbol='BTC-USDT-SWAP',
        route='trend',
        status=LivePositionStatus.EXIT_VERIFYING,
        side='short',
        size=0.14,
        reason='exit_verification_timeout',
        meta={
            'strategy_stats_eligible': 'false',
            'strategy_stats_reason': 'forced_exit_recovery',
            'execution_recovery': 'forced_exit',
            'execution_recovery_detail': 'exit_verification_timeout',
        },
    )
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='trend', account='trend', action='hold', reason='pending_verification:exit_verifying'),
        receipt=ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account='trend',
            symbol='BTC-USDT-SWAP',
            action='exit',
            side=None,
            size=0.14,
            order_id='x1',
            reason='forced_exit_recovery',
            observed_at=datetime.now(UTC),
            raw={'account_alias': 'trend', 'fee_usdt': 0.04, 'realized_pnl_usdt': 1.2},
            execution_id='exec-x',
            client_order_id='cl-x',
            trade_ids=['tx-a'],
        ),
        local_position=local,
        verification_position=local,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=False, diagnostics=['verify_only']),
        runtime_state={'mode': 'trade'},
        route_state=None,
        live_positions=[asdict(local)],
        router_composite={},
    )
    artifact = build_execution_artifact(result)
    assert artifact['summary']['strategy_stats_eligible'] is False
    assert artifact['summary']['strategy_stats_reason'] == 'forced_exit_recovery'
    assert artifact['summary']['attribution_fee_source'] == 'order_payload'
    assert artifact['summary']['attribution_realized_pnl_source'] == 'order_payload'
    assert artifact['summary']['attribution_trade_count'] == 1

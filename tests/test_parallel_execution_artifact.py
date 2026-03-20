from datetime import UTC, datetime

from src.execution.adapters import ExecutionReceipt
from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace, ParallelExecutionCycleResult
from src.reconcile.alignment import AlignmentResult
from src.runners.execution_cycle import build_parallel_execution_artifact
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.execution.controller import RouteControlResult
from src.execution.policy import PolicyDecision
from src.strategies.executors import ExecutionPlan


def _single_result(account: str) -> ExecutionCycleResult:
    return ExecutionCycleResult(
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
            route_decision={'regime': 'trend', 'account': account, 'strategy_family': account, 'trade_enabled': True, 'allow_reason': f'always_on_{account}', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': account, 'strategy_family': account, 'trade_enabled': True, 'allow_reason': f'always_on_{account}', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['parallel_execution']},
        ),
        plan=ExecutionPlan(regime='trend', account=account, action='enter', side='short', size=1.0, reason='test'),
        receipt=ExecutionReceipt(accepted=True, mode='okx_demo', account=account, symbol='BTC-USDT-SWAP', action='entry', side='short', size=1.0, order_id=f'ord-{account}', reason='test', observed_at=datetime.now(UTC), raw={}, execution_id=f'exec-{account}', client_order_id=f'cl-{account}', trade_ids=[]),
        local_position=None,
        verification_position=None,
        reconcile_result=RouteControlResult(alignment=AlignmentResult(ok=True, issues=[]), policy=PolicyDecision(trade_enabled=True, action='continue', reason='alignment_ok'), position=None),
        decision_trace=ExecutionDecisionTrace(mode=RuntimeMode.TRADE.value, mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True, pipeline_entered=True, submission_allowed=True, submission_attempted=True, allow_reason=f'always_on_{account}', block_reason=None, diagnostics=['parallel_execution']),
        runtime_state={'mode': RuntimeMode.TRADE.value},
        route_state={'enabled': True, 'frozen_reason': None},
        live_positions=[],
        router_composite={'selected_strategy': 'trend', 'position_owner': 'trend', 'plan': {'action': 'enter'}, 'position': {'side': 'short'}},
    )


def test_build_parallel_execution_artifact_contains_strategy_results():
    shared = _single_result('trend').regime_output
    result = ParallelExecutionCycleResult(
        regime_output=shared,
        results={'trend': _single_result('trend'), 'crowded': _single_result('crowded')},
        runtime_state={'mode': RuntimeMode.TRADE.value},
        live_positions=[],
        router_composite={'selected_strategy': 'trend', 'position_owner': 'trend', 'plan': {'action': 'enter'}, 'position': {'side': 'short'}},
    )
    artifact = build_parallel_execution_artifact(result)
    assert artifact['artifact_type'] == 'parallel_execution_cycle'
    assert set(artifact['results'].keys()) == {'trend', 'crowded'}
    assert artifact['summary']['strategy_results']['trend']['plan_account'] == 'trend'
    assert 'trend' in artifact['summary']['accepted_accounts']

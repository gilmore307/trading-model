from datetime import UTC, datetime
from pathlib import Path

from src.execution.adapters import ExecutionReceipt
from src.execution.controller import RouteController
from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace
from src.execution.policy import PolicyDecision
from src.reconcile.alignment import AlignmentResult, ExchangePositionSnapshot
from src.regime.classifier import RegimeOutput, StrategyPlan
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore
from src.runners.execution_cycle import build_execution_artifact


def build_controller(tmp_path: Path) -> RouteController:
    return RouteController(
        store=LiveStateStore(path=tmp_path / 'live-state.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )


def test_verify_exit_updates_pending_exit_allocations_and_closes_legs(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e2', entry_execution_id='exec-2', entry_client_order_id='cl-2', entry_trade_ids=['t2'])
    pos = c.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1', exit_execution_id='exec-x', exit_client_order_id='cl-x', exit_trade_ids=['tx'])
    assert pos and pos.pending_exit

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side=None, size=0.0))
    assert pos is not None
    assert pos.status.value == 'flat'
    assert len(pos.open_legs) == 0
    assert len(pos.closed_legs) == 2
    assert pos.pending_exit is not None
    assert pos.pending_exit.status == 'closed'
    assert [a.closed_size for a in pos.pending_exit.allocations] == [0.14, 0.14]


def test_execution_artifact_includes_ledger_snapshot():
    regime_output = RegimeOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 1.0, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': 'trend', 'confidence': 1.0, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={},
        primary_features={},
        override_features={},
        final_decision={'primary': 'trend', 'confidence': 1.0, 'reasons': [], 'secondary': [], 'tradable': True},
        route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
        decision_summary={'regime': 'trend', 'confidence': 1.0, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': []},
    )
    controller = build_controller(Path('/tmp'))
    pos = controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=StrategyPlan(regime='trend', account='trend', action='enter', side='short', size=1.0, reason='trend_follow_through_confirmed'),
        receipt=ExecutionReceipt(accepted=True, mode='okx_demo', account='trend', symbol='BTC-USDT-SWAP', action='entry', side='short', size=0.14, order_id='e1', reason='trend_follow_through_confirmed', observed_at=datetime.now(UTC), raw={'account_alias': 'trend'}, execution_id='exec-1', client_order_id='cl-1', trade_ids=['t1']),
        local_position=pos,
        verification_position=pos,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True, allow_reason='route_to_trend', block_reason=None, diagnostics=[]),
        runtime_state={'mode': 'trade'},
        route_state=None,
        live_positions=[pos],
        router_composite={},
    )
    artifact = build_execution_artifact(result)
    assert artifact['summary']['execution_id'] == 'exec-1'
    assert artifact['summary']['open_leg_count'] == 1
    assert artifact['ledger_snapshot']['open_legs'][0]['leg_id'] == 'exec-1'

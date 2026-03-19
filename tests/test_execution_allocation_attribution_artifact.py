from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.execution.adapters import ExecutionReceipt
from src.execution.controller import RouteController
from src.execution.pipeline import ExecutionCycleResult, ExecutionDecisionTrace
from src.reconcile.alignment import ExchangePositionSnapshot
from src.runners.regime_runner import RegimeRunnerOutput
from src.runners.execution_cycle import build_execution_artifact
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore
from src.strategies.executors import ExecutionPlan


def build_controller(tmp_path: Path) -> RouteController:
    return RouteController(
        store=LiveStateStore(path=tmp_path / 'live-state.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )


def test_execution_artifact_includes_pending_exit_allocation_attribution(tmp_path: Path):
    controller = build_controller(tmp_path)
    controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e2', entry_execution_id='exec-2', entry_client_order_id='cl-2', entry_trade_ids=['t2'])
    pos = controller.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1', exit_execution_id='exec-x', exit_client_order_id='cl-x', exit_trade_ids=['tx-a', 'tx-b'], requested_size=0.28)
    assert pos is not None and pos.pending_exit is not None
    pos.meta['last_exit_fee_usdt'] = 0.06
    pos.meta['last_exit_realized_pnl_usdt'] = 3.0
    controller.store.upsert(pos)
    pos = controller.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side=None, size=0.0))
    assert pos is not None

    regime_output = RegimeRunnerOutput(
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
    result = ExecutionCycleResult(
        regime_output=regime_output,
        plan=ExecutionPlan(regime='trend', account='trend', action='exit', reason='test_exit'),
        receipt=ExecutionReceipt(accepted=True, mode='okx_demo', account='trend', symbol='BTC-USDT-SWAP', action='exit', side=None, size=0.28, order_id='x1', reason='test_exit', observed_at=datetime.now(UTC), raw={'account_alias': 'trend', 'fee_usdt': 0.06, 'realized_pnl_usdt': 3.0}, execution_id='exec-x', client_order_id='cl-x', trade_ids=['tx-a', 'tx-b']),
        local_position=pos,
        verification_position=pos,
        reconcile_result=None,
        decision_trace=ExecutionDecisionTrace(mode='trade', mode_allows_routing=True, decision_trade_enabled=True, route_trade_enabled=True, pipeline_trade_enabled=True),
        runtime_state={'mode': 'trade'},
        route_state=None,
        live_positions=[asdict(pos)],
        router_composite={},
    )
    artifact = build_execution_artifact(result)
    allocs = artifact['ledger_snapshot']['pending_exit']['allocations']
    assert len(allocs) == 2
    assert allocs[0]['trade_ids'] == ['tx-a', 'tx-b']
    assert allocs[0]['fee_usdt'] == 0.03
    assert allocs[0]['realized_pnl_usdt'] == 1.5
    assert allocs[1]['fee_usdt'] == 0.03
    assert allocs[1]['realized_pnl_usdt'] == 1.5

    attr_allocs = artifact['attribution_snapshot']['pending_exit_allocations']
    assert len(attr_allocs) == 2
    assert attr_allocs[0]['trade_ids'] == ['tx-a', 'tx-b']
    assert attr_allocs[0]['fee_usdt'] == 0.03
    assert attr_allocs[0]['realized_pnl_usdt'] == 1.5

from datetime import UTC, datetime
from pathlib import Path

from src.execution.adapters import ExecutionAdapter, ExecutionReceipt
from src.execution.controller import RouteController
from src.execution.pipeline import ExecutionPipeline
from src.reconcile.alignment import ExchangePositionSnapshot
from src.routing.composite import RouterCompositeSimulator
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore
from src.strategies.executors import ExecutionPlan


class DummyRunner:
    def run_once(self):
        return RegimeRunnerOutput(
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


class HoldPipeline(ExecutionPipeline):
    def build_plan(self, output):
        return ExecutionPlan(regime='trend', account='trend', action='hold', reason='monitor')


class RecoveryAwareAdapter(ExecutionAdapter):
    def __init__(self):
        self.exit_calls = 0

    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        raise NotImplementedError

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        self.exit_calls += 1
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='exit',
            side=None,
            size=requested_size,
            order_id='x-recovery',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'verified_flat': False, 'verification_attempts': [{'attempt': 'initial', 'delay_seconds': 0.0, 'matched': False}]},
            execution_id='exec-recovery',
            client_order_id='cl-recovery',
            trade_ids=['tx-r'],
        )


class StickySnapshotProvider:
    def fetch_position(self, account: str, symbol: str):
        return ExchangePositionSnapshot(account=account, symbol=symbol, side='short', size=0.14)


def build_controller(tmp_path: Path) -> RouteController:
    return RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )


def test_forced_recovery_does_not_duplicate_when_pending_exit_exists(tmp_path: Path):
    controller = build_controller(tmp_path)
    controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    current = controller.store.get('trend', 'BTC-USDT-SWAP')
    assert current is not None
    current.status = current.status.OPEN
    controller.store.upsert(current)
    controller.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1', exit_execution_id='exec-x', exit_client_order_id='cl-x', exit_trade_ids=['tx-a'], requested_size=0.14)
    current = controller.store.get('trend', 'BTC-USDT-SWAP')
    assert current is not None
    current.status = current.status.EXIT_VERIFYING
    controller.store.upsert(current)

    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    adapter = RecoveryAwareAdapter()
    pipe = HoldPipeline(
        regime_runner=DummyRunner(),
        controller=controller,
        snapshot_provider=StickySnapshotProvider(),
        adapter=adapter,
        runtime_store=store,
        composite_simulator=RouterCompositeSimulator(controller.store),
    )

    result1 = pipe.run_cycle(None)
    result2 = pipe.run_cycle(None)

    assert adapter.exit_calls == 0
    assert result1.verification_position is not None
    assert result2.verification_position is not None
    assert result2.verification_position.status.value == 'exit_verifying'
    history = result2.verification_position.meta.get('event_history') or []
    assert not any(evt.get('kind') == 'forced_exit_recovery_marked' for evt in history)


def test_partial_exit_timeout_preserves_remaining_open_leg(tmp_path: Path):
    controller = build_controller(tmp_path)
    controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    controller.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e2', entry_execution_id='exec-2', entry_client_order_id='cl-2', entry_trade_ids=['t2'])
    current = controller.store.get('trend', 'BTC-USDT-SWAP')
    assert current is not None
    current.status = current.status.OPEN
    controller.store.upsert(current)
    pos = controller.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1', exit_execution_id='exec-x', exit_client_order_id='cl-x', exit_trade_ids=['tx-a'], requested_size=0.14)
    assert pos is not None
    pos = controller.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=0.14))
    assert pos is not None
    assert pos.pending_exit is not None
    assert pos.pending_exit.status == 'closed'
    assert len(pos.closed_legs) == 1
    assert len(pos.open_legs) == 1
    assert pos.open_legs[0].leg_id == 'exec-2'
    assert pos.open_legs[0].remaining_size == 0.14

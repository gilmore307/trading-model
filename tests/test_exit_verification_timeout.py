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


class ExitPipeline(ExecutionPipeline):
    def build_plan(self, output):
        return ExecutionPlan(regime='trend', account='trend', action='exit', reason='test_exit')


class FakeAdapter(ExecutionAdapter):
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        raise NotImplementedError

    def submit_exit(self, *, account: str, symbol: str, reason: str) -> ExecutionReceipt:
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='exit',
            side=None,
            size=None,
            order_id='x1',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'verified_flat': False, 'verification_attempts': [{'attempt': 'initial', 'delay_seconds': 0.0, 'matched': False}]},
            execution_id='exec-x',
            client_order_id='cl-x',
            trade_ids=[],
        )


class StickySnapshotProvider:
    def fetch_position(self, account: str, symbol: str):
        return ExchangePositionSnapshot(account=account, symbol=symbol, side='short', size=1.0)


def test_exit_verification_times_out_but_does_not_duplicate_submit(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    controller.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 1.0,
        entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'],
    )
    current = controller.store.get('trend', 'BTC-USDT-SWAP')
    assert current is not None
    current.status = current.status.OPEN
    controller.store.upsert(current)

    pipe = ExitPipeline(
        regime_runner=DummyRunner(),
        controller=controller,
        snapshot_provider=StickySnapshotProvider(),
        adapter=FakeAdapter(),
        runtime_store=store,
        composite_simulator=RouterCompositeSimulator(controller.store),
    )

    result1 = pipe.run_cycle(None)
    assert result1.verification_position is not None
    assert result1.verification_position.status.value == 'exit_verifying'

    result2 = pipe.run_cycle(None)
    assert result2.verification_position is not None
    assert result2.verification_position.status.value == 'exit_verifying'
    assert result2.verification_position.reason == 'exit_verification_timeout'
    history = result2.verification_position.meta.get('event_history') or []
    assert any(evt.get('kind') == 'exit_verification_timeout' for evt in history)

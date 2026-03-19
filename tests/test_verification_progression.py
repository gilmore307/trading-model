from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.execution.pipeline import ExecutionPipeline
from src.strategies.executors import ExecutionPlan
from src.execution.adapters import ExecutionAdapter, ExecutionReceipt
from src.reconcile.alignment import ExchangePositionSnapshot
from src.routing.composite import RouterCompositeSimulator
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore
from src.execution.controller import RouteController


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


class TestPipeline(ExecutionPipeline):
    def build_plan(self, output):
        return ExecutionPlan(regime='trend', account='trend', action='enter', side='short', size=1.0, reason='test_entry')


class FakeAdapter(ExecutionAdapter):
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='entry',
            side=side,
            size=size,
            order_id='ord-1',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'verified_entry': False, 'verification_attempts': [{'attempt': 'initial', 'delay_seconds': 0.0, 'matched': False}]},
            execution_id='exec-1',
            client_order_id='cl-1',
            trade_ids=[],
        )

    def submit_exit(self, *, account: str, symbol: str, reason: str) -> ExecutionReceipt:
        raise NotImplementedError


class SnapshotProvider:
    def __init__(self):
        self.calls = 0

    def fetch_position(self, account: str, symbol: str):
        self.calls += 1
        if self.calls == 1:
            return None
        return ExchangePositionSnapshot(account=account, symbol=symbol, side='short', size=1.0)


def test_pipeline_keeps_entry_verifying_and_confirms_on_later_cycle(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(store=LiveStateStore(path=tmp_path / 'live.json'), routes=RouteRegistry(path=tmp_path / 'routes.json'))
    snapshot_provider = SnapshotProvider()
    pipe = TestPipeline(
        regime_runner=DummyRunner(),
        controller=controller,
        snapshot_provider=snapshot_provider,
        adapter=FakeAdapter(),
        runtime_store=store,
        composite_simulator=RouterCompositeSimulator(controller.store),
    )

    result1 = pipe.run_cycle(None)
    assert result1.verification_position is not None
    assert result1.verification_position.status.value == 'entry_verifying'
    assert result1.local_position is not None
    assert result1.local_position.meta.get('last_verification_hint', {}).get('verified_entry') is False

    result2 = pipe.run_cycle(None)
    assert result2.verification_position is not None
    assert result2.verification_position.status.value == 'open'

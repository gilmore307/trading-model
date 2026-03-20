from datetime import UTC, datetime
from pathlib import Path

from src.execution.pipeline import ExecutionPipeline
from src.strategies.executors import ExecutionPlan
from src.execution.adapters import ExecutionAdapter, ExecutionReceipt
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


class NullSnapshotProvider:
    def fetch_position(self, account: str, symbol: str):
        return None


def test_entry_verification_times_out_after_configured_cycles(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    pipe = TestPipeline(
        regime_runner=DummyRunner(),
        controller=controller,
        snapshot_provider=NullSnapshotProvider(),
        adapter=FakeAdapter(),
        runtime_store=store,
        composite_simulator=RouterCompositeSimulator(controller.store),
    )

    result1 = pipe.run_cycle(None)
    assert result1.verification_position is not None
    assert result1.verification_position.status.value == 'entry_verifying'

    result2 = pipe.run_cycle(None)
    assert result2.verification_position is not None
    assert result2.verification_position.status.value == 'flat'
    assert result2.verification_position.reason == 'entry_verification_timeout'
    assert result2.verification_position.meta.get('execution_recovery') == 'missed_entry'
    assert result2.verification_position.open_legs == []
    assert result2.verification_position.pending_exit is None
    assert result2.verification_position.entry_trade_ids == []
    assert controller.routes.is_enabled('trend', 'BTC-USDT-SWAP') is True
    history = result2.verification_position.meta.get('event_history') or []
    assert any(evt.get('kind') == 'missed_entry_cleared' for evt in history)

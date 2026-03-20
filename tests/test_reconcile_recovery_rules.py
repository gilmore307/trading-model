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


class EntryPipeline(ExecutionPipeline):
    def build_plan(self, output):
        return ExecutionPlan(regime='trend', account='trend', action='enter', side='short', size=1.0, reason='test_entry')


class EntryAdapter(ExecutionAdapter):
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='entry',
            side=side,
            size=12.74,
            order_id='ord-1',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'verified_entry': False, 'verification_attempts': []},
            execution_id='exec-1',
            client_order_id='cl-1',
            trade_ids=['t1'],
        )

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        raise NotImplementedError


class EntrySnapshotProvider:
    def fetch_position(self, account: str, symbol: str):
        return ExchangePositionSnapshot(account=account, symbol=symbol, side='short', size=12.74)


def test_entry_ledger_uses_receipt_size_not_plan_unit(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    pipe = EntryPipeline(
        regime_runner=DummyRunner(),
        controller=controller,
        snapshot_provider=EntrySnapshotProvider(),
        adapter=EntryAdapter(),
        runtime_store=store,
        composite_simulator=RouterCompositeSimulator(controller.store),
    )

    result = pipe.run_cycle(None)
    assert result.local_position is not None
    assert result.local_position.open_legs
    leg = result.local_position.open_legs[0]
    assert leg.requested_size == 12.74
    assert leg.filled_size == 12.74
    assert result.local_position.size == 12.74


def test_reconcile_mismatch_still_participates_in_alignment(tmp_path: Path):
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    pos = controller.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 12.88,
        entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'],
    )
    pos.status = pos.status.RECONCILE_MISMATCH
    controller.store.upsert(pos)

    snap = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=12.88)
    result = controller.reconcile_account_symbol('trend', 'BTC-USDT-SWAP', snap)
    assert result.alignment.ok is True
    assert result.policy.trade_enabled is True

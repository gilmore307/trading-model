from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.execution.adapters import ExecutionAdapter, ExecutionReceipt
from src.execution.controller import RouteController
from src.execution.pipeline import ExecutionPipeline
from src.reconcile.alignment import ExchangePositionSnapshot
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


class DummyAdapter(ExecutionAdapter):
    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='entry',
            side=side,
            size=0.27,
            order_id='entry-1',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={'amount': 0.27},
        )

    def submit_exit(self, *, account: str, symbol: str, reason: str) -> ExecutionReceipt:
        return ExecutionReceipt(
            accepted=True,
            mode='okx_demo',
            account=account,
            symbol=symbol,
            action='exit',
            side=None,
            size=None,
            order_id='exit-1',
            reason=reason,
            observed_at=datetime.now(UTC),
            raw={},
        )


class DummyRunner:
    def __init__(self, regime='trend', account='trend', trade_enabled=True):
        self.regime = regime
        self.account = account
        self.trade_enabled = trade_enabled

    def run_once(self):
        return RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': self.regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={'ema20_slope': 1.0},
            primary_features={'vwap_deviation_z': 1.0, 'basis_deviation_pct': 0.01},
            override_features={'vwap_deviation_z': 1.0},
            final_decision={'primary': self.regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': self.trade_enabled},
            route_decision={'regime': self.regime, 'account': self.account, 'strategy_family': self.regime, 'trade_enabled': self.trade_enabled, 'block_reason': None if self.trade_enabled else 'no_route_for_regime', 'allow_reason': None if not self.trade_enabled else f'route_to_{self.account}'},
            decision_summary={'regime': self.regime, 'confidence': 0.8, 'tradable': self.trade_enabled, 'account': self.account, 'strategy_family': self.regime, 'trade_enabled': self.trade_enabled, 'allow_reason': None if not self.trade_enabled else f'route_to_{self.account}', 'block_reason': None if self.trade_enabled else 'no_route_for_regime', 'reasons': [], 'secondary': [], 'diagnostics': []},
        )


def test_execution_pipeline_enters_and_verifies_via_controller(tmp_path: Path):
    runner = DummyRunner(regime='trend', account='trend', trade_enabled=True)
    out = runner.run_once()
    out.background_features['adx'] = 32.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 28.0
    out.primary_features['vwap_deviation_z'] = 0.9
    out.override_features['vwap_deviation_z'] = 1.0
    out.override_features['trade_burst_score'] = 0.7
    runner.run_once = lambda: out
    controller = RouteController(store=LiveStateStore(path=tmp_path / 'live-state.json'), routes=RouteRegistry(path=tmp_path / 'routes.json'))
    pipe = ExecutionPipeline(regime_runner=runner, controller=controller, snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0)})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'enter'
    assert result.receipt is not None
    assert result.receipt.accepted is True
    assert result.local_position is not None
    assert result.verification_position is not None
    assert result.verification_position.status.value == 'open'


def test_execution_pipeline_holds_when_route_disabled():
    pipe = ExecutionPipeline(regime_runner=DummyRunner(regime='chaotic', account=None, trade_enabled=False), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'hold'
    assert result.local_position is None
    assert result.decision_trace.block_reason == 'no_route_for_regime'
    assert 'decision_gate_blocked' in result.decision_trace.diagnostics


def test_execution_pipeline_range_enter_submits_order():
    runner = DummyRunner(regime='range', account='meanrev', trade_enabled=True)
    out = runner.run_once()
    out.background_features['adx'] = 15.0
    out.background_features['ema20_slope'] = 0.1
    out.background_features['ema50_slope'] = 0.0
    out.primary_features['adx'] = 14.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.18
    out.primary_features['vwap_deviation_z'] = 1.1
    out.override_features['vwap_deviation_z'] = 0.8
    out.override_features['trade_burst_score'] = 0.0
    runner.run_once = lambda: out
    pipe = ExecutionPipeline(regime_runner=runner, snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='meanrev', symbol='BTC-USDT-SWAP', side='short', size=1.0)})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'enter'
    assert result.receipt is not None
    assert result.receipt.accepted is True


def test_execution_pipeline_crowded_enter_submits_order():
    runner = DummyRunner(regime='crowded', account='crowded', trade_enabled=True)
    out = runner.run_once()
    out.primary_features['funding_pctile'] = 0.97
    out.primary_features['oi_accel'] = 0.2
    out.primary_features['basis_deviation_pct'] = 0.006
    out.primary_features['vwap_deviation_z'] = 1.4
    out.override_features['trade_burst_score'] = 0.2
    out.override_features['vwap_deviation_z'] = 0.8
    runner.run_once = lambda: out
    pipe = ExecutionPipeline(regime_runner=runner, snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='crowded', symbol='BTC-USDT-SWAP', side='short', size=1.0)})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'enter'
    assert result.receipt is not None
    assert result.receipt.accepted is True


def test_execution_pipeline_shock_enter_submits_order():
    runner = DummyRunner(regime='shock', account='realtime', trade_enabled=True)
    out = runner.run_once()
    out.override_features['vwap_deviation_z'] = 2.0
    out.override_features['trade_burst_score'] = 0.8
    out.override_features['liquidation_spike_score'] = 0.5
    out.override_features['orderbook_imbalance'] = 0.6
    out.override_features['realized_vol_pct'] = 0.9
    runner.run_once = lambda: out
    pipe = ExecutionPipeline(regime_runner=runner, snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='realtime', symbol='BTC-USDT-SWAP', side='short', size=1.0)})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'enter'
    assert result.receipt is not None
    assert result.receipt.accepted is True


def test_execution_pipeline_arm_does_not_submit_order():
    runner = DummyRunner(regime='compression', account='compression', trade_enabled=True)
    out = runner.run_once()
    out.background_features['ema20_slope'] = 1.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.01
    out.primary_features['realized_vol_pct'] = 0.08
    out.primary_features['vwap_deviation_z'] = 0.95
    out.override_features['vwap_deviation_z'] = 0.9
    runner.run_once = lambda: out
    pipe = ExecutionPipeline(regime_runner=runner, snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})())
    result = pipe.run_cycle(None)
    assert result.plan.action == 'arm'
    assert result.receipt is None


def test_execution_pipeline_uses_exchange_snapshot_as_authoritative_size_after_entry(tmp_path: Path):
    runner = DummyRunner(regime='trend', account='trend', trade_enabled=True)
    out = runner.run_once()
    out.background_features['adx'] = 32.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 28.0
    out.primary_features['vwap_deviation_z'] = 0.9
    out.override_features['vwap_deviation_z'] = 1.0
    out.override_features['trade_burst_score'] = 0.7
    runner.run_once = lambda: out

    class SnapshotProvider:
        def __init__(self):
            self.calls = 0

        def fetch_position(self, account, symbol):
            self.calls += 1
            if self.calls == 1:
                return None
            return ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=0.27)

    snapshots = SnapshotProvider()
    runtime_store = RuntimeStore()
    runtime_store.set_mode(RuntimeMode.TRADE, reason='test_trade_mode')
    controller = RouteController(store=LiveStateStore(path=tmp_path / 'live-state.json'), routes=RouteRegistry(path=tmp_path / 'routes.json'))
    pipe = ExecutionPipeline(regime_runner=runner, controller=controller, snapshot_provider=snapshots, adapter=DummyAdapter(), runtime_store=runtime_store)
    result = pipe.run_cycle(None)
    assert result.receipt is not None
    assert result.receipt.size == 0.27
    assert result.local_position is not None
    assert result.local_position.size == 0.27
    assert result.verification_position is not None
    assert result.verification_position.status.value == 'open'
    assert snapshots.calls >= 2


def test_execution_pipeline_prefers_post_submit_exchange_contracts_over_receipt_size(tmp_path: Path):
    runner = DummyRunner(regime='trend', account='trend', trade_enabled=True)
    out = runner.run_once()
    out.background_features['adx'] = 32.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 28.0
    out.primary_features['vwap_deviation_z'] = 0.9
    out.override_features['vwap_deviation_z'] = 1.0
    out.override_features['trade_burst_score'] = 0.7
    runner.run_once = lambda: out

    class MismatchAdapter(ExecutionAdapter):
        def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
            return ExecutionReceipt(
                accepted=True,
                mode='okx_demo',
                account=account,
                symbol=symbol,
                action='entry',
                side=side,
                size=99.0,
                order_id='entry-1',
                reason=reason,
                observed_at=datetime.now(UTC),
                raw={'amount': 99.0},
            )

        def submit_exit(self, *, account: str, symbol: str, reason: str) -> ExecutionReceipt:
            raise AssertionError('submit_exit should not be called')

    class SnapshotProvider:
        def __init__(self):
            self.calls = 0

        def fetch_position(self, account, symbol):
            self.calls += 1
            if self.calls == 1:
                return None
            return ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=0.27)

    snapshots = SnapshotProvider()
    runtime_store = RuntimeStore()
    runtime_store.set_mode(RuntimeMode.TRADE, reason='test_trade_mode')
    controller = RouteController(store=LiveStateStore(path=tmp_path / 'live-state.json'), routes=RouteRegistry(path=tmp_path / 'routes.json'))
    pipe = ExecutionPipeline(regime_runner=runner, controller=controller, snapshot_provider=snapshots, adapter=MismatchAdapter(), runtime_store=runtime_store)
    result = pipe.run_cycle(None)
    assert result.receipt is not None
    assert result.receipt.size == 99.0
    assert result.local_position is not None
    assert result.local_position.size == 0.27
    assert result.verification_position is not None
    assert result.verification_position.size == 0.27
    assert result.reconcile_result is not None
    assert result.reconcile_result.alignment.ok is True

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


class DummyRunner:
    def run_once(self):
        return RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={'adx': 32.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
            primary_features={'adx': 28.0, 'vwap_deviation_z': 1.4, 'bollinger_bandwidth_pct': 0.03, 'funding_pctile': 0.95, 'oi_accel': 0.2, 'basis_deviation_pct': 0.005, 'realized_vol_pct': 0.05},
            override_features={'vwap_deviation_z': 1.2, 'trade_burst_score': 0.9, 'liquidation_spike_score': 0.6, 'orderbook_imbalance': 0.5, 'realized_vol_pct': 1.0},
            final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['high_confidence']},
        )


class RecordingAdapter(ExecutionAdapter):
    def __init__(self):
        self.entries = []
        self.exits = []

    def submit_entry(self, *, account: str, symbol: str, side: str, size: float, reason: str) -> ExecutionReceipt:
        self.entries.append((account, symbol, side, size, reason))
        return ExecutionReceipt(accepted=True, mode='okx_demo', account=account, symbol=symbol, action='entry', side=side, size=size, order_id=f'ord-{account}', reason=reason, observed_at=datetime.now(UTC), raw={'verified_entry': False, 'verification_attempts': []}, execution_id=f'exec-{account}', client_order_id=f'cl-{account}', trade_ids=[])

    def submit_exit(self, *, account: str, symbol: str, reason: str, requested_size: float | None = None) -> ExecutionReceipt:
        self.exits.append((account, symbol, requested_size, reason))
        return ExecutionReceipt(accepted=True, mode='okx_demo', account=account, symbol=symbol, action='exit', side=None, size=requested_size, order_id=f'exit-{account}', reason=reason, observed_at=datetime.now(UTC), raw={'verified_flat': True, 'verification_attempts': []}, execution_id=f'exit-exec-{account}', client_order_id=f'exit-cl-{account}', trade_ids=[])


class FlatSnapshots:
    def fetch_position(self, account: str, symbol: str):
        return None


def test_run_cycle_parallel_returns_per_strategy_results(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(store=LiveStateStore(path=tmp_path / 'live.json'), routes=RouteRegistry(path=tmp_path / 'routes.json'), verification_cycle_timeout=2)
    adapter = RecordingAdapter()
    pipe = ExecutionPipeline(regime_runner=DummyRunner(), snapshot_provider=FlatSnapshots(), runtime_store=store, controller=controller, adapter=adapter)

    result = pipe.run_cycle_parallel()
    assert set(result.results.keys()) == {'trend', 'range', 'compression', 'crowded', 'shock'}
    assert result.results['trend'].plan.account == 'trend'
    assert result.results['range'].plan.account == 'meanrev'
    assert result.results['compression'].plan.account == 'compression'
    assert result.results['crowded'].plan.account == 'crowded'
    assert result.results['shock'].plan.account == 'realtime'
    assert any(entry[0] == 'trend' for entry in adapter.entries)

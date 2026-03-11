from dataclasses import dataclass
from datetime import UTC, datetime

from src.execution.pipeline import ExecutionPipeline
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runners.regime_runner import RegimeRunnerOutput


class DummyRunner:
    def run_once(self):
        return RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={'adx': 32.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
            primary_features={'adx': 28.0, 'vwap_deviation_z': 0.9, 'bollinger_bandwidth_pct': 0.03},
            override_features={'vwap_deviation_z': 1.0, 'trade_burst_score': 0.7},
            final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True},
        )


def test_calibrate_mode_blocks_normal_routing():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.CALIBRATE, 'weekly')
    pipe = ExecutionPipeline(regime_runner=DummyRunner(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})(), runtime_store=store)
    result = pipe.run_cycle(None)
    assert result.plan.action == 'hold'
    assert result.plan.reason == 'mode_blocked:calibrate'


def test_develop_mode_forces_dry_run_adapter_behavior():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.DEVELOP, 'dev')
    pipe = ExecutionPipeline(regime_runner=DummyRunner(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})(), runtime_store=store)
    result = pipe.run_cycle(None)
    assert result.receipt is not None
    assert result.receipt.mode == 'dry_run'

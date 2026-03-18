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
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['high_confidence']},
        )


def test_calibrate_mode_blocks_strategy_execution_and_normal_routing():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.CALIBRATE, 'weekly')
    pipe = ExecutionPipeline(regime_runner=DummyRunner(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})(), runtime_store=store)
    result = pipe.run_cycle(None)
    assert result.plan.action == 'hold'
    assert result.plan.reason == 'mode_no_strategy:calibrate'
    assert result.decision_trace.block_reason == 'mode_no_strategy:calibrate'
    assert 'strategy_execution_disabled' in result.decision_trace.diagnostics


def test_develop_mode_blocks_strategy_execution_and_stays_idle():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.DEVELOP, 'dev')
    pipe = ExecutionPipeline(regime_runner=DummyRunner(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})(), runtime_store=store)
    result = pipe.run_cycle(None)
    assert result.receipt is None
    assert result.plan.action == 'hold'
    assert result.plan.reason == 'mode_no_strategy:develop'
    assert result.decision_trace.pipeline_trade_enabled is False
    assert result.decision_trace.block_reason == 'mode_no_strategy:develop'
    assert 'strategy_execution_disabled' in result.decision_trace.diagnostics

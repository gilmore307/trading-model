from dataclasses import dataclass
from datetime import UTC, datetime

from pathlib import Path

from src.execution.controller import RouteController
from src.execution.pipeline import ExecutionPipeline
from src.reconcile.alignment import ExchangePositionSnapshot
from src.runners.regime_runner import RegimeRunnerOutput
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


class DummyRunnerLowConfidence:
    def run_once(self):
        return RegimeRunnerOutput(
            observed_at=datetime.now(UTC),
            symbol='BTC-USDT-SWAP',
            background_4h={'primary': 'trend', 'confidence': 0.25, 'reasons': [], 'secondary': [], 'tradable': True},
            primary_15m={'primary': 'trend', 'confidence': 0.25, 'reasons': [], 'secondary': [], 'tradable': True},
            override_1m=None,
            background_features={'adx': 32.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
            primary_features={'adx': 28.0, 'vwap_deviation_z': 0.9, 'bollinger_bandwidth_pct': 0.03},
            override_features={'vwap_deviation_z': 1.0, 'trade_burst_score': 0.7},
            final_decision={'primary': 'trend', 'confidence': 0.25, 'reasons': ['thin_confirmation'], 'secondary': ['range'], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.25, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': False, 'allow_reason': None, 'block_reason': 'confidence_too_low', 'reasons': ['thin_confirmation'], 'secondary': ['range'], 'diagnostics': ['low_confidence', 'confidence_gate_blocked']},
        )


class DummyRunnerTrend:
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


def test_pipeline_holds_when_decision_summary_blocks_trade():
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    pipe = ExecutionPipeline(regime_runner=DummyRunnerLowConfidence(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})(), runtime_store=store)
    result = pipe.run_cycle(None)
    assert result.plan.action == 'hold'
    assert result.plan.reason == 'confidence_too_low'
    assert result.decision_trace.block_reason == 'confidence_too_low'
    assert 'decision_gate_blocked' in result.decision_trace.diagnostics


def test_pipeline_trace_captures_alignment_freeze_reason(tmp_path: Path):
    store = RuntimeStore()
    store.set_mode(RuntimeMode.TRADE, 'test')
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    pipe = ExecutionPipeline(
        regime_runner=DummyRunnerTrend(),
        snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=3.0)})(),
        runtime_store=store,
        controller=controller,
    )
    result = pipe.run_cycle(None)
    assert result.reconcile_result is not None
    assert result.reconcile_result.policy.trade_enabled is True
    assert result.reconcile_result.policy.reason == 'alignment_ok'
    assert result.decision_trace.block_reason is None
    assert 'freeze_route' not in result.decision_trace.diagnostics

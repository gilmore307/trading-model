from dataclasses import dataclass
from datetime import UTC, datetime

from src.execution.pipeline import ExecutionPipeline
from src.reconcile.alignment import ExchangePositionSnapshot
from src.runtime.mode import RuntimeMode
from src.runtime.store import RuntimeStore
from src.runners.regime_runner import RegimeRunnerOutput


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


def test_pipeline_emits_runtime_route_and_live_position_snapshots():
    runtime_store = RuntimeStore()
    runtime_store.set_mode(RuntimeMode.TRADE, 'manual')
    pipe = ExecutionPipeline(
        regime_runner=DummyRunnerTrend(),
        snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0)})(),
        runtime_store=runtime_store,
    )
    result = pipe.run_cycle(None)
    assert result.runtime_state['mode'] == RuntimeMode.TRADE
    assert result.route_state is not None
    assert result.route_state['account'] == 'trend'
    assert result.route_state['enabled'] is True
    assert len(result.live_positions) == 1
    assert result.live_positions[0]['account'] == 'trend'
    assert result.live_positions[0]['symbol'] == 'BTC-USDT-SWAP'
    assert result.router_composite['account'] == 'router_composite'
    assert result.router_composite['selected_strategy'] == 'trend'

from datetime import UTC, datetime

from src.execution.pipeline import ExecutionPipeline
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
            primary_features={'adx': 28.0, 'vwap_deviation_z': 0.9, 'bollinger_bandwidth_pct': 0.03, 'funding_pctile': 0.95, 'oi_accel': 0.2, 'basis_deviation_pct': 0.005},
            override_features={'vwap_deviation_z': 1.0, 'trade_burst_score': 0.7, 'liquidation_spike_score': 0.6, 'orderbook_imbalance': 0.5, 'realized_vol_pct': 1.0},
            final_decision={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
            route_decision={'regime': 'trend', 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None},
            decision_summary={'regime': 'trend', 'confidence': 0.8, 'tradable': True, 'account': 'trend', 'strategy_family': 'trend', 'trade_enabled': True, 'allow_reason': 'route_to_trend', 'block_reason': None, 'reasons': [], 'secondary': [], 'diagnostics': ['high_confidence']},
        )


def test_build_parallel_plans_assigns_all_accounts():
    pipe = ExecutionPipeline(regime_runner=DummyRunnerTrend(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})())
    output = pipe.regime_runner.run_once()
    plans = pipe.build_parallel_plans(output)

    assert set(plans.keys()) == {'trend', 'range', 'compression', 'crowded', 'shock'}
    assert plans['trend'].account == 'trend'
    assert plans['range'].account == 'meanrev'
    assert plans['compression'].account == 'compression'
    assert plans['crowded'].account == 'crowded'
    assert plans['shock'].account == 'realtime'


def test_build_parallel_plans_not_limited_by_single_router_selection():
    pipe = ExecutionPipeline(regime_runner=DummyRunnerTrend(), snapshot_provider=type('SP', (), {'fetch_position': lambda self, a, s: None})())
    output = pipe.regime_runner.run_once()
    plans = pipe.build_parallel_plans(output)

    assert all(plan.account is not None for plan in plans.values())
    assert plans['crowded'].account == 'crowded'
    assert plans['shock'].account == 'realtime'

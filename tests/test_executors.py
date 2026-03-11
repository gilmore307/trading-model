from datetime import UTC, datetime

from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import executor_for


def _out(regime, account='trend', trade_enabled=True):
    return RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={'ema20_slope': 1.0},
        primary_features={'vwap_deviation_z': 1.0, 'basis_deviation_pct': 0.01},
        override_features={'vwap_deviation_z': 1.0},
        final_decision={'primary': regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': trade_enabled},
        route_decision={'regime': regime, 'account': account if trade_enabled else None, 'strategy_family': regime, 'trade_enabled': trade_enabled},
    )


def test_executor_for_trend_builds_watch_plan_when_weak_follow_through():
    out = _out('trend')
    out.background_features['adx'] = 30.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 18.0
    out.primary_features['vwap_deviation_z'] = 0.2
    out.override_features['vwap_deviation_z'] = 0.1
    out.override_features['trade_burst_score'] = 0.0
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'watch'


def test_executor_for_trend_builds_arm_plan():
    out = _out('trend')
    out.background_features['adx'] = 30.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 24.0
    out.primary_features['vwap_deviation_z'] = 0.7
    out.primary_features['bollinger_bandwidth_pct'] = 0.03
    out.override_features['vwap_deviation_z'] = 0.3
    out.override_features['trade_burst_score'] = 0.0
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'arm'
    assert plan.side == 'long'


def test_executor_for_trend_builds_enter_plan():
    out = _out('trend')
    out.background_features['adx'] = 32.0
    out.background_features['ema20_slope'] = 1.0
    out.background_features['ema50_slope'] = 0.8
    out.primary_features['adx'] = 28.0
    out.primary_features['vwap_deviation_z'] = 0.9
    out.override_features['vwap_deviation_z'] = 1.0
    out.override_features['trade_burst_score'] = 0.7
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'enter'
    assert plan.side == 'long'


def test_executor_for_range_builds_watch_plan():
    out = _out('range', account='meanrev')
    out.primary_features['adx'] = 25.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.20
    out.primary_features['vwap_deviation_z'] = 0.4
    out.override_features['vwap_deviation_z'] = 0.1
    out.override_features['trade_burst_score'] = 0.0
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'watch'


def test_executor_for_range_builds_arm_plan():
    out = _out('range', account='meanrev')
    out.background_features['adx'] = 15.0
    out.background_features['ema20_slope'] = 0.1
    out.background_features['ema50_slope'] = 0.0
    out.primary_features['adx'] = 16.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.20
    out.primary_features['vwap_deviation_z'] = 0.9
    out.override_features['vwap_deviation_z'] = 0.4
    out.override_features['trade_burst_score'] = 0.0
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'arm'
    assert plan.side == 'short'


def test_executor_for_range_builds_enter_plan():
    out = _out('range', account='meanrev')
    out.background_features['adx'] = 15.0
    out.background_features['ema20_slope'] = 0.1
    out.background_features['ema50_slope'] = 0.0
    out.primary_features['adx'] = 14.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.18
    out.primary_features['vwap_deviation_z'] = 1.1
    out.override_features['vwap_deviation_z'] = 0.8
    out.override_features['trade_burst_score'] = 0.0
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'enter'
    assert plan.side == 'short'


def test_executor_for_shock_builds_watch_plan():
    out = _out('shock', account='realtime')
    out.override_features['vwap_deviation_z'] = 0.8
    out.override_features['trade_burst_score'] = 0.1
    out.override_features['liquidation_spike_score'] = 0.0
    out.override_features['orderbook_imbalance'] = 0.1
    out.override_features['realized_vol_pct'] = 0.5
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'watch'


def test_executor_for_shock_builds_arm_plan():
    out = _out('shock', account='realtime')
    out.override_features['vwap_deviation_z'] = 1.8
    out.override_features['trade_burst_score'] = 0.7
    out.override_features['liquidation_spike_score'] = 0.0
    out.override_features['orderbook_imbalance'] = 0.2
    out.override_features['realized_vol_pct'] = 0.7
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'arm'
    assert plan.side == 'short'


def test_executor_for_shock_builds_enter_plan():
    out = _out('shock', account='realtime')
    out.override_features['vwap_deviation_z'] = 2.0
    out.override_features['trade_burst_score'] = 0.8
    out.override_features['liquidation_spike_score'] = 0.5
    out.override_features['orderbook_imbalance'] = 0.6
    out.override_features['realized_vol_pct'] = 0.9
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'enter'
    assert plan.side == 'short'


def test_executor_for_crowded_builds_watch_plan():
    out = _out('crowded', account='crowded')
    out.primary_features['funding_pctile'] = 0.6
    out.primary_features['oi_accel'] = 0.05
    out.primary_features['basis_deviation_pct'] = 0.001
    out.primary_features['vwap_deviation_z'] = 0.8
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'watch'


def test_executor_for_crowded_builds_arm_plan():
    out = _out('crowded', account='crowded')
    out.primary_features['funding_pctile'] = 0.95
    out.primary_features['oi_accel'] = 0.2
    out.primary_features['basis_deviation_pct'] = 0.005
    out.primary_features['vwap_deviation_z'] = 0.9
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'arm'
    assert plan.side == 'short'


def test_executor_for_crowded_builds_enter_plan():
    out = _out('crowded', account='crowded')
    out.primary_features['funding_pctile'] = 0.97
    out.primary_features['oi_accel'] = 0.2
    out.primary_features['basis_deviation_pct'] = 0.006
    out.primary_features['vwap_deviation_z'] = 1.4
    out.override_features['trade_burst_score'] = 0.2
    out.override_features['vwap_deviation_z'] = 0.8
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'enter'
    assert plan.side == 'short'


def test_executor_for_compression_builds_watch_plan():
    out = _out('compression', account='compression')
    out.primary_features['bollinger_bandwidth_pct'] = 0.05
    out.primary_features['realized_vol_pct'] = 0.3
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'watch'


def test_executor_for_compression_builds_arm_plan():
    out = _out('compression', account='compression')
    out.background_features['ema20_slope'] = 1.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.01
    out.primary_features['realized_vol_pct'] = 0.08
    out.primary_features['vwap_deviation_z'] = 0.95
    out.override_features['vwap_deviation_z'] = 0.9
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'arm'


def test_executor_for_compression_builds_enter_plan():
    out = _out('compression', account='compression')
    out.background_features['ema20_slope'] = 1.0
    out.primary_features['bollinger_bandwidth_pct'] = 0.01
    out.primary_features['realized_vol_pct'] = 0.05
    out.primary_features['vwap_deviation_z'] = 1.1
    out.override_features['vwap_deviation_z'] = 1.2
    out.override_features['trade_burst_score'] = 0.8
    plan = executor_for(out).build_plan(out)
    assert plan.action == 'enter'
    assert plan.side == 'long'


def test_executor_for_disabled_route_builds_hold_plan():
    plan = executor_for(_out('chaotic', account=None, trade_enabled=False)).build_plan(_out('chaotic', account=None, trade_enabled=False))
    assert plan.action == 'hold'

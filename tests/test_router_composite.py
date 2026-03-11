from datetime import UTC, datetime

from src.routing.composite import COMPOSITE_ACCOUNT, RouterCompositeSimulator
from src.runners.regime_runner import RegimeRunnerOutput
from src.state.live_position import LivePosition, LivePositionStatus
from src.state.store import LiveStateStore


def _output(regime='trend', account='trend', trade_enabled=True):
    return RegimeRunnerOutput(
        observed_at=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        background_4h={'primary': 'trend', 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        primary_15m={'primary': regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': True},
        override_1m=None,
        background_features={'adx': 32.0, 'ema20_slope': 1.0, 'ema50_slope': 0.8},
        primary_features={'adx': 28.0, 'vwap_deviation_z': 0.9, 'basis_deviation_pct': 0.01, 'bollinger_bandwidth_pct': 0.03},
        override_features={'vwap_deviation_z': 1.0, 'trade_burst_score': 0.7},
        final_decision={'primary': regime, 'confidence': 0.8, 'reasons': [], 'secondary': [], 'tradable': trade_enabled},
        route_decision={'regime': regime, 'account': account if trade_enabled else None, 'strategy_family': account if trade_enabled else None, 'trade_enabled': trade_enabled, 'allow_reason': None if not trade_enabled else f'route_to_{account}', 'block_reason': None if trade_enabled else 'no_route_for_regime'},
        decision_summary={'regime': regime, 'confidence': 0.8, 'tradable': trade_enabled, 'account': account if trade_enabled else None, 'strategy_family': account if trade_enabled else None, 'trade_enabled': trade_enabled, 'allow_reason': None if not trade_enabled else f'route_to_{account}', 'block_reason': None if trade_enabled else 'regime_non_tradable', 'reasons': [], 'secondary': [], 'diagnostics': []},
    )


def test_router_composite_follows_router_selected_strategy():
    sim = RouterCompositeSimulator()
    snap = sim.snapshot(_output('trend', 'trend', True))
    assert snap['account'] == COMPOSITE_ACCOUNT
    assert snap['selected_strategy'] == 'trend'
    assert snap['plan']['account'] == COMPOSITE_ACCOUNT
    assert snap['plan']['action'] in {'enter', 'arm', 'watch'}
    if snap['position'] is not None:
        assert snap['position_owner'] == 'trend'
        assert snap['position']['meta']['opened_by_strategy'] == 'trend'


def test_router_composite_holds_when_router_not_actionable():
    sim = RouterCompositeSimulator()
    snap = sim.snapshot(_output('chaotic', None, False))
    assert snap['selected_strategy'] is None
    assert snap['plan']['action'] == 'hold'
    assert 'router_not_actionable' in snap['notes']


def test_router_composite_keeps_when_target_strategy_has_same_direction_position():
    store = LiveStateStore()
    store.upsert(LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0))
    sim = RouterCompositeSimulator(store)
    sim._positions['BTC-USDT-SWAP'] = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='range', status=LivePositionStatus.OPEN, side='long', size=1.0)
    snap = sim.snapshot(_output('trend', 'trend', True))
    assert snap['switch_action'] == 'keep_current_position'
    assert snap['plan']['action'] == 'hold'
    assert 'target_position_side:long' in snap['notes']


def test_router_composite_closes_when_target_strategy_has_opposite_direction_position():
    store = LiveStateStore()
    store.upsert(LivePosition(account='crowded', symbol='BTC-USDT-SWAP', route='crowded', status=LivePositionStatus.OPEN, side='short', size=1.0))
    sim = RouterCompositeSimulator(store)
    sim._positions['BTC-USDT-SWAP'] = LivePosition(account='router_composite', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0)
    snap = sim.snapshot(_output('crowded', 'crowded', True))
    assert snap['switch_action'] == 'close_and_wait'
    assert snap['plan']['action'] == 'exit'
    assert 'target_position_side:short' in snap['notes']

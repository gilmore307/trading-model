from pathlib import Path

from src.state.execution_ledger import ExecutionLeg
from src.state.live_position import LivePosition, LivePositionStatus
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


def test_live_state_store_persists_positions(tmp_path: Path):
    path = tmp_path / 'live-state.json'
    store = LiveStateStore(path=path)
    store.upsert(LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=0.27, entry_order_id='abc'))

    restored = LiveStateStore(path=path)
    pos = restored.get('trend', 'BTC-USDT-SWAP')
    assert pos is not None
    assert pos.status == LivePositionStatus.OPEN
    assert pos.side == 'long'
    assert pos.size == 0.27
    assert pos.entry_order_id == 'abc'


def test_live_state_store_persists_execution_legs(tmp_path: Path):
    path = tmp_path / 'live-state.json'
    store = LiveStateStore(path=path)
    store.upsert(LivePosition(
        account='trend',
        symbol='BTC-USDT-SWAP',
        route='trend',
        status=LivePositionStatus.OPEN,
        side='short',
        size=0.42,
        open_legs=[ExecutionLeg(leg_id='leg-1', execution_id='exec-1', client_order_id='cl-1', order_id='ord-1', trade_ids=['t1'], side='short', requested_size=0.14, filled_size=0.14, remaining_size=0.14)],
    ))

    restored = LiveStateStore(path=path)
    pos = restored.get('trend', 'BTC-USDT-SWAP')
    assert pos is not None
    assert len(pos.open_legs) == 1
    assert pos.open_legs[0].execution_id == 'exec-1'
    assert pos.open_legs[0].client_order_id == 'cl-1'
    assert pos.open_legs[0].trade_ids == ['t1']


def test_route_registry_persists_frozen_state(tmp_path: Path):
    path = tmp_path / 'route-registry.json'
    routes = RouteRegistry(path=path)
    routes.freeze('trend', 'BTC-USDT-SWAP', 'severe_alignment_issue')

    restored = RouteRegistry(path=path)
    state = restored.get('trend', 'BTC-USDT-SWAP')
    assert state.enabled is False
    assert state.frozen_reason == 'severe_alignment_issue'

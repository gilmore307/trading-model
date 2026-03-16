from pathlib import Path

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


def test_route_registry_persists_frozen_state(tmp_path: Path):
    path = tmp_path / 'route-registry.json'
    routes = RouteRegistry(path=path)
    routes.freeze('trend', 'BTC-USDT-SWAP', 'severe_alignment_issue')

    restored = RouteRegistry(path=path)
    state = restored.get('trend', 'BTC-USDT-SWAP')
    assert state.enabled is False
    assert state.frozen_reason == 'severe_alignment_issue'

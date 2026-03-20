from pathlib import Path

from src.execution.controller import RouteController
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


def test_mark_missed_entry_clears_local_execution_state(tmp_path: Path):
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
        verification_cycle_timeout=2,
    )
    pos = controller.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 12.74,
        entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'],
    )
    assert pos.open_legs

    cleaned = controller.mark_missed_entry('trend', 'BTC-USDT-SWAP', detail='manual_test')
    assert cleaned is not None
    assert cleaned.status.value == 'flat'
    assert cleaned.side is None
    assert cleaned.size == 0.0
    assert cleaned.open_legs == []
    assert cleaned.pending_exit is None
    assert cleaned.entry_order_id is None
    assert cleaned.entry_execution_id is None
    assert cleaned.entry_client_order_id is None
    assert cleaned.entry_trade_ids == []
    assert controller.routes.is_enabled('trend', 'BTC-USDT-SWAP') is True
    history = cleaned.meta.get('event_history') or []
    assert any(evt.get('kind') == 'missed_entry_cleared' for evt in history)

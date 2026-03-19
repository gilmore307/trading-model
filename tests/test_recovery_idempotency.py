from pathlib import Path

from src.execution.controller import RouteController
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


def test_forced_exit_recovery_mark_is_idempotent(tmp_path: Path):
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )
    controller.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 1.0,
        entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'],
    )

    pos1 = controller.mark_forced_exit_recovery('trend', 'BTC-USDT-SWAP', detail='forced_exit_recovery_submitted')
    pos2 = controller.mark_forced_exit_recovery('trend', 'BTC-USDT-SWAP', detail='forced_exit_recovery_submitted')

    assert pos1 is not None and pos2 is not None
    assert pos2.meta.get('execution_recovery') == 'forced_exit'
    history = pos2.meta.get('event_history') or []
    assert any(evt.get('kind') == 'forced_exit_recovery_marked' for evt in history)
    assert any(evt.get('kind') == 'forced_exit_recovery_duplicate_ignored' for evt in history)

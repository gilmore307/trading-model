from pathlib import Path

from src.execution.controller import RouteController
from src.reconcile.alignment import ExchangePositionSnapshot
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


def build_controller(tmp_path: Path) -> RouteController:
    return RouteController(
        store=LiveStateStore(path=tmp_path / 'live-state.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )


def test_partial_exit_only_closes_allocated_size(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'])
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14, entry_order_id='e2', entry_execution_id='exec-2', entry_client_order_id='cl-2', entry_trade_ids=['t2'])

    pos = c.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1', exit_execution_id='exec-x', exit_client_order_id='cl-x', exit_trade_ids=['tx'], requested_size=0.14)
    assert pos is not None and pos.pending_exit is not None
    pos.meta['last_exit_fee_usdt'] = 0.02
    pos.meta['last_exit_realized_pnl_usdt'] = 1.4
    c.store.upsert(pos)
    assert pos.pending_exit.requested_size == 0.14
    assert [a.requested_size for a in pos.pending_exit.allocations] == [0.14]

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=0.14))
    assert pos is not None
    assert pos.pending_exit is not None
    assert pos.pending_exit.status == 'closed'
    assert [a.closed_size for a in pos.pending_exit.allocations] == [0.14]
    assert pos.pending_exit.allocations[0].trade_ids == ['tx']
    assert pos.pending_exit.allocations[0].fee_usdt == 0.02
    assert pos.pending_exit.allocations[0].realized_pnl_usdt == 1.4
    assert len(pos.closed_legs) == 1
    assert len(pos.open_legs) == 1
    assert pos.open_legs[0].leg_id == 'exec-2'
    assert pos.open_legs[0].remaining_size == 0.14

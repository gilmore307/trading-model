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


def test_multi_allocation_exit_distributes_fee_and_realized_pnl_by_closed_size(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14,
        entry_order_id='e1', entry_execution_id='exec-1', entry_client_order_id='cl-1', entry_trade_ids=['t1'],
    )
    c.submit_entry(
        'trend', 'BTC-USDT-SWAP', 'trend', 'short', 0.14,
        entry_order_id='e2', entry_execution_id='exec-2', entry_client_order_id='cl-2', entry_trade_ids=['t2'],
    )

    pos = c.submit_exit(
        'trend', 'BTC-USDT-SWAP',
        exit_order_id='x1',
        exit_execution_id='exec-x',
        exit_client_order_id='cl-x',
        exit_trade_ids=['tx-a', 'tx-b'],
        requested_size=0.28,
    )
    assert pos is not None and pos.pending_exit is not None
    pos.meta['last_exit_fee_usdt'] = 0.06
    pos.meta['last_exit_realized_pnl_usdt'] = 3.0
    c.store.upsert(pos)

    pos = c.verify_position(
        'trend',
        'BTC-USDT-SWAP',
        ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side=None, size=0.0),
    )
    assert pos is not None
    assert pos.pending_exit is not None
    assert pos.pending_exit.status == 'closed'
    assert len(pos.pending_exit.allocations) == 2

    alloc1, alloc2 = pos.pending_exit.allocations
    assert alloc1.leg_id == 'exec-1'
    assert alloc2.leg_id == 'exec-2'
    assert alloc1.closed_size == 0.14
    assert alloc2.closed_size == 0.14
    assert alloc1.trade_ids == ['tx-a', 'tx-b']
    assert alloc2.trade_ids == ['tx-a', 'tx-b']
    assert alloc1.fee_usdt == 0.03
    assert alloc2.fee_usdt == 0.03
    assert alloc1.realized_pnl_usdt == 1.5
    assert alloc2.realized_pnl_usdt == 1.5
    assert len(pos.closed_legs) == 2
    assert len(pos.open_legs) == 0

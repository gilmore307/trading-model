from pathlib import Path

from src.execution.adapters import DryRunExecutionAdapter
from src.execution.controller import RouteController
from src.state.store import LiveStateStore
from src.state.route_registry import RouteRegistry


def test_dry_run_receipts_include_execution_trace_ids():
    adapter = DryRunExecutionAdapter()
    receipt = adapter.submit_entry(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0, reason='test')
    assert receipt.execution_id is not None
    assert receipt.client_order_id is not None
    assert receipt.trade_ids == []
    assert receipt.raw['execution_id'] == receipt.execution_id
    assert receipt.raw['client_order_id'] == receipt.client_order_id


def test_route_controller_persists_entry_and_exit_trace_ids(tmp_path: Path):
    controller = RouteController(
        store=LiveStateStore(path=tmp_path / 'live-state.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )
    pos = controller.submit_entry(
        'trend',
        'BTC-USDT-SWAP',
        'trend',
        'short',
        1.0,
        entry_order_id='ord-1',
        entry_execution_id='exec-1',
        entry_client_order_id='cl-1',
        entry_trade_ids=['t1', 't2'],
    )
    assert pos.entry_execution_id == 'exec-1'
    assert pos.entry_client_order_id == 'cl-1'
    assert pos.entry_trade_ids == ['t1', 't2']

    pos = controller.submit_exit(
        'trend',
        'BTC-USDT-SWAP',
        exit_order_id='ord-2',
        exit_execution_id='exec-2',
        exit_client_order_id='cl-2',
        exit_trade_ids=['t3'],
    )
    assert pos is not None
    assert pos.exit_execution_id == 'exec-2'
    assert pos.exit_client_order_id == 'cl-2'
    assert pos.exit_trade_ids == ['t3']

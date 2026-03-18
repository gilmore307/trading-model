from pathlib import Path

from src.execution.controller import RouteController
from src.reconcile.alignment import ExchangePositionSnapshot, AlignmentIssueType
from src.state.live_position import LivePositionStatus
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


def build_controller(tmp_path: Path) -> RouteController:
    return RouteController(
        store=LiveStateStore(path=tmp_path / 'live-state.json'),
        routes=RouteRegistry(path=tmp_path / 'routes.json'),
    )


def test_route_controller_entry_verify_open_flow(tmp_path: Path):
    c = build_controller(tmp_path)
    pos = c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    assert pos.status == LivePositionStatus.ENTRY_SUBMITTED

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', None)
    assert pos.status == LivePositionStatus.ENTRY_VERIFYING

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert pos.status == LivePositionStatus.OPEN


def test_route_controller_exit_verify_flat_flow(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))

    pos = c.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1')
    assert pos.status == LivePositionStatus.EXIT_SUBMITTED

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert pos.status == LivePositionStatus.EXIT_VERIFYING

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', None)
    assert pos.status == LivePositionStatus.FLAT
    assert pos.size == 0.0
    assert pos.side is None


def test_route_controller_reconcile_freezes_on_unexpected_exchange_position(tmp_path: Path):
    c = build_controller(tmp_path)
    result = c.reconcile_account_symbol('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert result.alignment.ok is False
    assert result.alignment.issues[0].type == AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION
    assert result.policy.trade_enabled is False
    assert result.policy.action == 'freeze_route'


def test_route_controller_marks_forced_exit_recovery_metadata(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    c.submit_exit('trend', 'BTC-USDT-SWAP', exit_order_id='x1')
    c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    pos = c.mark_forced_exit_recovery('trend', 'BTC-USDT-SWAP', detail='forced_exit_recovery_submitted')
    assert pos is not None
    assert pos.meta['strategy_stats_eligible'] == 'false'
    assert pos.meta['strategy_stats_reason'] == 'forced_exit_recovery'
    assert pos.meta['execution_recovery'] == 'forced_exit'


def test_route_controller_marks_missed_entry_and_clears_local_position(tmp_path: Path):
    c = build_controller(tmp_path)
    c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    pos = c.mark_missed_entry('trend', 'BTC-USDT-SWAP', detail='missed_entry_not_opened_on_exchange')
    assert pos is not None
    assert pos.status == LivePositionStatus.FLAT
    assert pos.side is None
    assert pos.size == 0.0
    assert pos.meta['strategy_stats_eligible'] == 'false'
    assert pos.meta['strategy_stats_reason'] == 'missed_entry'
    assert pos.meta['execution_recovery'] == 'missed_entry'

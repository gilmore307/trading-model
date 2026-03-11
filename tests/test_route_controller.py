from src.execution.controller import RouteController
from src.reconcile.alignment import ExchangePositionSnapshot, AlignmentIssueType
from src.state.live_position import LivePositionStatus


def test_route_controller_entry_verify_open_flow():
    c = RouteController()
    pos = c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    assert pos.status == LivePositionStatus.ENTRY_SUBMITTED

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', None)
    assert pos.status == LivePositionStatus.ENTRY_VERIFYING

    pos = c.verify_position('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert pos.status == LivePositionStatus.OPEN


def test_route_controller_exit_verify_flat_flow():
    c = RouteController()
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


def test_route_controller_reconcile_freezes_on_unexpected_exchange_position():
    c = RouteController()
    result = c.reconcile_account_symbol('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert result.alignment.ok is False
    assert result.alignment.issues[0].type == AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION
    assert result.policy.trade_enabled is False
    assert result.policy.action == 'freeze_route'

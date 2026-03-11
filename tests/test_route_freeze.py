from src.execution.controller import RouteController
from src.reconcile.alignment import ExchangePositionSnapshot
from src.state.live_position import LivePositionStatus


def test_reconcile_freezes_route_on_unexpected_exchange_position():
    c = RouteController()
    result = c.reconcile_account_symbol('trend', 'BTC-USDT-SWAP', ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0))
    assert result.policy.action == 'freeze_route'
    assert c.routes.is_enabled('trend', 'BTC-USDT-SWAP') is False


def test_submit_entry_respects_frozen_route():
    c = RouteController()
    c.routes.freeze('trend', 'BTC-USDT-SWAP', 'severe_alignment_issue')
    pos = c.submit_entry('trend', 'BTC-USDT-SWAP', 'trend', 'long', 1.0, entry_order_id='e1')
    assert pos.status == LivePositionStatus.DISABLED
    assert pos.reason == 'severe_alignment_issue'

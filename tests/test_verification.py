from src.execution.confirm import verify_entry, verify_exit
from src.reconcile.alignment import ExchangePositionSnapshot
from src.state.live_position import LivePosition, LivePositionStatus


def test_verify_entry_requires_exchange_confirmation():
    local = LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.ENTRY_VERIFYING, side='long', size=1.0)
    decision = verify_entry(local, None)
    assert decision.next_status == LivePositionStatus.ENTRY_VERIFYING
    assert decision.accepted is False


def test_verify_entry_opens_after_exchange_confirmation():
    local = LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.ENTRY_VERIFYING, side='long', size=1.0)
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0)
    decision = verify_entry(local, exchange)
    assert decision.next_status == LivePositionStatus.OPEN
    assert decision.accepted is True


def test_verify_exit_only_flats_after_exchange_flat_confirmation():
    local = LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.EXIT_VERIFYING, side='long', size=1.0)
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0)
    decision = verify_exit(local, exchange)
    assert decision.next_status == LivePositionStatus.EXIT_VERIFYING
    assert decision.accepted is False

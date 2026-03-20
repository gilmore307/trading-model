from datetime import UTC, datetime

from src.execution.confirm import verify_entry
from src.state.execution_ledger import ExecutionLeg
from src.state.live_position import LivePosition, LivePositionStatus
from src.reconcile.alignment import ExchangePositionSnapshot


def _local_position(*, size: float, trade_confirmed: bool = False, has_trade_ids: bool | None = None) -> LivePosition:
    pos = LivePosition(
        account='trend',
        symbol='BTC-USDT-SWAP',
        route='trend',
        status=LivePositionStatus.ENTRY_SUBMITTED,
        side='short',
        size=size,
        open_legs=[
            ExecutionLeg(
                leg_id='leg-1',
                execution_id='exec-1',
                client_order_id='cl-1',
                order_id='ord-1',
                trade_ids=['t1'] if (trade_confirmed or has_trade_ids) else [],
                action='entry',
                side='short',
                requested_size=size,
                filled_size=size,
                remaining_size=size,
                status='open',
                opened_at=datetime.now(UTC),
            )
        ],
        meta={
            'last_verification_hint': {
                'verified_entry': trade_confirmed,
                'verification_attempts': [
                    {'attempt': 'initial', 'delay_seconds': 0.0, 'trade_confirmed': trade_confirmed}
                ],
            }
        },
    )
    if trade_confirmed or has_trade_ids:
        pos.entry_trade_ids = ['t1']
    return pos


def test_verify_entry_accepts_trade_confirmed_matching_size():
    local = _local_position(size=12.74, trade_confirmed=True)
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=12.74)
    decision = verify_entry(local, exchange)
    assert decision.accepted is True
    assert decision.next_status == LivePositionStatus.OPEN
    assert decision.reason == 'exchange_position_trade_confirmed'


def test_verify_entry_accepts_trade_ids_matching_size_even_without_verified_flag():
    local = _local_position(size=12.74, trade_confirmed=False, has_trade_ids=True)
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=12.74)
    decision = verify_entry(local, exchange)
    assert decision.accepted is True
    assert decision.next_status == LivePositionStatus.OPEN
    assert decision.reason == 'exchange_position_trade_ids_confirmed'


def test_verify_entry_rejects_size_mismatch_even_if_position_exists():
    local = _local_position(size=12.74, trade_confirmed=False)
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=10.0)
    decision = verify_entry(local, exchange)
    assert decision.accepted is False
    assert decision.next_status == LivePositionStatus.ENTRY_VERIFYING
    assert decision.reason == 'exchange_position_size_unconfirmed'

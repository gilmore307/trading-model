from src.reconcile.alignment import ExchangePositionSnapshot, AlignmentIssueType, reconcile_positions
from src.state.live_position import LivePosition, LivePositionStatus


def test_closed_like_states_do_not_participate_in_alignment():
    local = [
        LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.RECONCILE_MISMATCH, side='long', size=1.0),
    ]
    exchange = []
    result = reconcile_positions(local, exchange)
    assert result.ok is True
    assert result.issues == []


def test_missing_exchange_position_detected_for_live_local_position():
    local = [
        LivePosition(account='trend', symbol='BTC-USDT-SWAP', route='trend', status=LivePositionStatus.OPEN, side='long', size=1.0),
    ]
    exchange = []
    result = reconcile_positions(local, exchange)
    assert result.ok is False
    assert result.issues[0].type == AlignmentIssueType.MISSING_EXCHANGE_POSITION


def test_unexpected_exchange_position_detected_when_no_local_live_position():
    local = []
    exchange = [ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0)]
    result = reconcile_positions(local, exchange)
    assert result.ok is False
    assert result.issues[0].type == AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION

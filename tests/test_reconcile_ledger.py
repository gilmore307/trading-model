from src.reconcile.alignment import AlignmentIssueType, ExchangePositionSnapshot, reconcile_positions
from src.state.execution_ledger import ExecutionLeg
from src.state.live_position import LivePosition, LivePositionStatus


def test_reconcile_detects_position_vs_ledger_mismatch():
    local = LivePosition(
        account='trend',
        symbol='BTC-USDT-SWAP',
        route='trend',
        status=LivePositionStatus.OPEN,
        side='short',
        size=0.7,
        open_legs=[
            ExecutionLeg(leg_id='leg-1', execution_id='exec-1', client_order_id='cl-1', order_id='o1', side='short', requested_size=0.14, filled_size=0.14, remaining_size=0.14),
            ExecutionLeg(leg_id='leg-2', execution_id='exec-2', client_order_id='cl-2', order_id='o2', side='short', requested_size=0.14, filled_size=0.14, remaining_size=0.14),
        ],
    )
    exchange = ExchangePositionSnapshot(account='trend', symbol='BTC-USDT-SWAP', side='short', size=0.28)
    result = reconcile_positions([local], [exchange])
    assert result.ok is False
    assert any(issue.type == AlignmentIssueType.LEDGER_POSITION_MISMATCH for issue in result.issues)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.state.execution_ledger import ExecutionLeg, ExitExecution


class LivePositionStatus(StrEnum):
    FLAT = 'flat'
    ENTRY_SUBMITTED = 'entry_submitted'
    ENTRY_VERIFYING = 'entry_verifying'
    OPEN = 'open'
    EXIT_SUBMITTED = 'exit_submitted'
    EXIT_VERIFYING = 'exit_verifying'
    RECONCILE_MISMATCH = 'reconcile_mismatch'
    DISABLED = 'disabled'


LIVE_ALIGNMENT_STATUSES = {
    LivePositionStatus.ENTRY_SUBMITTED,
    LivePositionStatus.ENTRY_VERIFYING,
    LivePositionStatus.OPEN,
    LivePositionStatus.EXIT_SUBMITTED,
    LivePositionStatus.EXIT_VERIFYING,
    LivePositionStatus.RECONCILE_MISMATCH,
}


@dataclass(slots=True)
class LivePosition:
    account: str
    symbol: str
    route: str
    status: LivePositionStatus = LivePositionStatus.FLAT
    side: str | None = None
    size: float = 0.0
    entry_order_id: str | None = None
    exit_order_id: str | None = None
    entry_execution_id: str | None = None
    exit_execution_id: str | None = None
    entry_client_order_id: str | None = None
    exit_client_order_id: str | None = None
    entry_trade_ids: list[str] | None = None
    exit_trade_ids: list[str] | None = None
    open_legs: list[ExecutionLeg] = field(default_factory=list)
    closed_legs: list[ExecutionLeg] = field(default_factory=list)
    pending_exit: ExitExecution | None = None
    last_exchange_observed_at: datetime | None = None
    last_local_updated_at: datetime | None = None
    reason: str | None = None
    meta: dict[str, str | float | list | dict | None] = field(default_factory=dict)

    def has_open_leg(self, *, execution_id: str | None = None, order_id: str | None = None, client_order_id: str | None = None) -> bool:
        for leg in self.open_legs:
            if execution_id and leg.execution_id == execution_id:
                return True
            if order_id and leg.order_id == order_id:
                return True
            if client_order_id and leg.client_order_id == client_order_id:
                return True
        return False

    @property
    def participates_in_alignment(self) -> bool:
        return self.status in LIVE_ALIGNMENT_STATUSES

    @property
    def ledger_open_size(self) -> float:
        if self.open_legs:
            return float(sum(float(leg.remaining_size or 0.0) for leg in self.open_legs))
        return float(self.size or 0.0)

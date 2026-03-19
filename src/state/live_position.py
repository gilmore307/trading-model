from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


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
    last_exchange_observed_at: datetime | None = None
    last_local_updated_at: datetime | None = None
    reason: str | None = None
    meta: dict[str, str | float | None] = field(default_factory=dict)

    @property
    def participates_in_alignment(self) -> bool:
        return self.status in LIVE_ALIGNMENT_STATUSES

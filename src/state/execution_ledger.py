from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ExitAllocation:
    leg_id: str
    requested_size: float
    closed_size: float = 0.0
    trade_ids: list[str] = field(default_factory=list)
    fee_usdt: float | None = None
    realized_pnl_usdt: float | None = None


@dataclass(slots=True)
class ExecutionLeg:
    leg_id: str
    execution_id: str | None
    client_order_id: str | None
    order_id: str | None
    trade_ids: list[str] = field(default_factory=list)
    action: str = 'entry'
    side: str | None = None
    requested_size: float = 0.0
    filled_size: float = 0.0
    remaining_size: float = 0.0
    status: str = 'open'
    reason: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    close_execution_id: str | None = None
    close_client_order_id: str | None = None
    close_order_id: str | None = None
    close_trade_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExitExecution:
    execution_id: str | None
    client_order_id: str | None
    order_id: str | None
    trade_ids: list[str] = field(default_factory=list)
    requested_size: float = 0.0
    side: str | None = None
    status: str = 'submitted'
    reason: str | None = None
    allocations: list[ExitAllocation] = field(default_factory=list)
    submitted_at: datetime | None = None

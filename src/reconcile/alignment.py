from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.state.live_position import LivePosition


class AlignmentIssueType(StrEnum):
    MISSING_EXCHANGE_POSITION = 'missing_exchange_position'
    UNEXPECTED_EXCHANGE_POSITION = 'unexpected_exchange_position'
    SIDE_MISMATCH = 'side_mismatch'
    SIZE_MISMATCH = 'size_mismatch'
    LEDGER_POSITION_MISMATCH = 'ledger_position_mismatch'
    STALE_LOCAL_STATE = 'stale_local_state'


@dataclass(slots=True)
class ExchangePositionSnapshot:
    account: str
    symbol: str
    side: str | None
    size: float


@dataclass(slots=True)
class AlignmentIssue:
    type: AlignmentIssueType
    account: str
    symbol: str
    local_status: str | None
    local_side: str | None
    local_size: float | None
    exchange_side: str | None
    exchange_size: float | None
    detail: str | None = None


@dataclass(slots=True)
class AlignmentResult:
    ok: bool
    issues: list[AlignmentIssue]


def reconcile_positions(
    local_positions: list[LivePosition],
    exchange_positions: list[ExchangePositionSnapshot],
    *,
    size_tolerance_ratio: float = 0.05,
    size_tolerance_abs: float = 1e-9,
) -> AlignmentResult:
    issues: list[AlignmentIssue] = []

    local_map = {
        (p.account, p.symbol): p
        for p in local_positions
        if p.participates_in_alignment
    }
    exchange_map = {
        (p.account, p.symbol): p
        for p in exchange_positions
        if abs(float(p.size or 0.0)) > 0.0
    }

    keys = sorted(set(local_map) | set(exchange_map))
    for key in keys:
        local = local_map.get(key)
        exchange = exchange_map.get(key)
        account, symbol = key

        if local and not exchange:
            issues.append(AlignmentIssue(
                type=AlignmentIssueType.MISSING_EXCHANGE_POSITION,
                account=account,
                symbol=symbol,
                local_status=local.status.value,
                local_side=local.side,
                local_size=local.ledger_open_size,
                exchange_side=None,
                exchange_size=None,
            ))
            continue

        if exchange and not local:
            issues.append(AlignmentIssue(
                type=AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION,
                account=account,
                symbol=symbol,
                local_status=None,
                local_side=None,
                local_size=None,
                exchange_side=exchange.side,
                exchange_size=exchange.size,
            ))
            continue

        if not local or not exchange:
            continue

        if local.side != exchange.side:
            issues.append(AlignmentIssue(
                type=AlignmentIssueType.SIDE_MISMATCH,
                account=account,
                symbol=symbol,
                local_status=local.status.value,
                local_side=local.side,
                local_size=local.ledger_open_size,
                exchange_side=exchange.side,
                exchange_size=exchange.size,
            ))
            continue

        local_size = float(local.ledger_open_size or 0.0)
        exchange_size = float(exchange.size or 0.0)
        diff = abs(local_size - exchange_size)
        allowed = max(size_tolerance_abs, abs(exchange_size) * size_tolerance_ratio)
        if diff > allowed:
            issues.append(AlignmentIssue(
                type=AlignmentIssueType.SIZE_MISMATCH,
                account=account,
                symbol=symbol,
                local_status=local.status.value,
                local_side=local.side,
                local_size=local_size,
                exchange_side=exchange.side,
                exchange_size=exchange_size,
                detail=f'diff={diff}, allowed={allowed}',
            ))

        position_size = float(local.size or 0.0)
        position_diff = abs(position_size - local_size)
        position_allowed = max(size_tolerance_abs, abs(local_size) * size_tolerance_ratio)
        if position_diff > position_allowed:
            issues.append(AlignmentIssue(
                type=AlignmentIssueType.LEDGER_POSITION_MISMATCH,
                account=account,
                symbol=symbol,
                local_status=local.status.value,
                local_side=local.side,
                local_size=position_size,
                exchange_side=local.side,
                exchange_size=local_size,
                detail=f'position_vs_ledger_diff={position_diff}, allowed={position_allowed}',
            ))

    return AlignmentResult(ok=not issues, issues=issues)

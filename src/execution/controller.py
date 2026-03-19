from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.state.execution_ledger import ExecutionLeg, ExitAllocation, ExitExecution

from src.execution.confirm import verify_entry, verify_exit
from src.execution.locks import AccountSymbolLockRegistry
from src.execution.policy import PolicyDecision, decide_alignment_policy
from src.reconcile.alignment import AlignmentResult, ExchangePositionSnapshot, reconcile_positions
from src.state.live_position import LivePosition, LivePositionStatus
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


@dataclass(slots=True)
class RouteControlResult:
    alignment: AlignmentResult
    policy: PolicyDecision
    position: LivePosition | None


class RouteController:
    def __init__(self, store: LiveStateStore | None = None, locks: AccountSymbolLockRegistry | None = None, routes: RouteRegistry | None = None):
        self.store = store or LiveStateStore()
        self.locks = locks or AccountSymbolLockRegistry()
        self.routes = routes or RouteRegistry()

    def mark_forced_exit_recovery(self, account: str, symbol: str, *, detail: str | None = None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            meta = dict(current.meta or {})
            meta['strategy_stats_eligible'] = 'false'
            meta['strategy_stats_reason'] = 'forced_exit_recovery'
            meta['execution_recovery'] = 'forced_exit'
            if detail is not None:
                meta['execution_recovery_detail'] = detail
            current.meta = meta
            current.reason = detail or 'forced_exit_recovery'
            return self.store.upsert(current)

    def enable_route_if_flat(self, account: str, symbol: str) -> bool:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                self.routes.enable(account, symbol)
                return True
            if current.status == LivePositionStatus.FLAT and float(current.size or 0.0) <= 0.0 and current.side is None:
                self.routes.enable(account, symbol)
                return True
            return False

    def mark_missed_entry(self, account: str, symbol: str, *, detail: str | None = None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            meta = dict(current.meta or {})
            meta['strategy_stats_eligible'] = 'false'
            meta['strategy_stats_reason'] = 'missed_entry'
            meta['execution_recovery'] = 'missed_entry'
            if detail is not None:
                meta['execution_recovery_detail'] = detail
            current.meta = meta
            current.status = LivePositionStatus.FLAT
            current.side = None
            current.size = 0.0
            current.reason = detail or 'missed_entry_cleared'
            return self.store.upsert(current)

    def submit_entry(
        self,
        account: str,
        symbol: str,
        route: str,
        side: str,
        size: float,
        entry_order_id: str | None = None,
        *,
        entry_execution_id: str | None = None,
        entry_client_order_id: str | None = None,
        entry_trade_ids: list[str] | None = None,
    ) -> LivePosition:
        with self.locks.hold(account, symbol):
            if not self.routes.is_enabled(account, symbol):
                current = self.store.get(account, symbol) or LivePosition(account=account, symbol=symbol, route=route)
                current.status = LivePositionStatus.DISABLED
                current.reason = self.routes.get(account, symbol).frozen_reason or 'route_disabled'
                return self.store.upsert(current)
            current = self.store.get(account, symbol)
            if current is None:
                current = LivePosition(account=account, symbol=symbol, route=route)
            current.status = LivePositionStatus.ENTRY_SUBMITTED
            current.side = side
            current.size = float(current.size or 0.0) + float(size or 0.0)
            current.entry_order_id = entry_order_id
            current.entry_execution_id = entry_execution_id
            current.entry_client_order_id = entry_client_order_id
            current.entry_trade_ids = list(entry_trade_ids or [])
            current.open_legs.append(ExecutionLeg(
                leg_id=entry_execution_id or entry_order_id or f'leg-{len(current.open_legs)+1}',
                execution_id=entry_execution_id,
                client_order_id=entry_client_order_id,
                order_id=entry_order_id,
                trade_ids=list(entry_trade_ids or []),
                action='entry',
                side=side,
                requested_size=float(size or 0.0),
                filled_size=float(size or 0.0),
                remaining_size=float(size or 0.0),
                status='open',
                reason='entry_submitted',
                opened_at=datetime.now(UTC),
            ))
            current.pending_exit = None
            current.reason = 'entry_submitted'
            return self.store.upsert(current)

    def submit_exit(
        self,
        account: str,
        symbol: str,
        exit_order_id: str | None = None,
        *,
        exit_execution_id: str | None = None,
        exit_client_order_id: str | None = None,
        exit_trade_ids: list[str] | None = None,
    ) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            current.status = LivePositionStatus.EXIT_SUBMITTED
            current.exit_order_id = exit_order_id
            current.exit_execution_id = exit_execution_id
            current.exit_client_order_id = exit_client_order_id
            current.exit_trade_ids = list(exit_trade_ids or [])
            remaining_to_allocate = float(current.ledger_open_size or current.size or 0.0)
            allocations: list[ExitAllocation] = []
            for leg in current.open_legs:
                if remaining_to_allocate <= 0:
                    break
                alloc_size = min(float(leg.remaining_size or 0.0), remaining_to_allocate)
                if alloc_size <= 0:
                    continue
                allocations.append(ExitAllocation(leg_id=leg.leg_id, requested_size=alloc_size, closed_size=0.0))
                remaining_to_allocate -= alloc_size
            current.pending_exit = ExitExecution(
                execution_id=exit_execution_id,
                client_order_id=exit_client_order_id,
                order_id=exit_order_id,
                trade_ids=list(exit_trade_ids or []),
                requested_size=float(current.ledger_open_size or current.size or 0.0),
                side=current.side,
                status='submitted',
                reason='exit_submitted',
                allocations=allocations,
                submitted_at=datetime.now(UTC),
            )
            current.reason = 'exit_submitted'
            return self.store.upsert(current)

    def refresh_local_position_from_exchange(self, account: str, symbol: str, exchange_snapshot: ExchangePositionSnapshot | None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None or exchange_snapshot is None:
                return current
            current.side = exchange_snapshot.side
            current.size = float(exchange_snapshot.size or 0.0)
            current.last_exchange_observed_at = datetime.now(UTC)
            current.reason = 'exchange_snapshot_refreshed'
            return self.store.upsert(current)

    def verify_position(self, account: str, symbol: str, exchange_snapshot: ExchangePositionSnapshot | None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None

            if exchange_snapshot is not None:
                current.side = exchange_snapshot.side
                current.size = float(exchange_snapshot.size or 0.0)
                current.last_exchange_observed_at = datetime.now(UTC)

            if current.open_legs and current.status in {LivePositionStatus.ENTRY_SUBMITTED, LivePositionStatus.ENTRY_VERIFYING, LivePositionStatus.OPEN} and exchange_snapshot is not None:
                total_before = sum(float(leg.remaining_size or 0.0) for leg in current.open_legs)
                exchange_size = float(exchange_snapshot.size or 0.0)
                delta = max(0.0, exchange_size - max(0.0, total_before - float(current.open_legs[-1].remaining_size or 0.0)))
                newest = current.open_legs[-1]
                newest.filled_size = max(float(newest.filled_size or 0.0), delta)
                newest.remaining_size = max(float(newest.remaining_size or 0.0), delta)
                newest.status = 'open'

            if current.pending_exit is not None:
                current.pending_exit.trade_ids = list(current.exit_trade_ids or current.pending_exit.trade_ids or [])
                current.pending_exit.order_id = current.exit_order_id or current.pending_exit.order_id

            if current.status in {LivePositionStatus.ENTRY_SUBMITTED, LivePositionStatus.ENTRY_VERIFYING}:
                decision = verify_entry(current, exchange_snapshot)
                current.status = decision.next_status
                current.reason = decision.reason
                return self.store.upsert(current)

            if current.status in {LivePositionStatus.EXIT_SUBMITTED, LivePositionStatus.EXIT_VERIFYING}:
                decision = verify_exit(current, exchange_snapshot)
                current.status = decision.next_status
                current.reason = decision.reason
                if decision.next_status == LivePositionStatus.FLAT:
                    current.side = None
                    current.size = 0.0
                    if current.pending_exit is not None:
                        for alloc in current.pending_exit.allocations:
                            alloc.closed_size = alloc.requested_size
                        current.pending_exit.status = 'closed'
                    remaining_open = []
                    for leg in current.open_legs:
                        leg.remaining_size = 0.0
                        leg.status = 'closed'
                        leg.closed_at = datetime.now(UTC)
                        leg.close_execution_id = current.exit_execution_id
                        leg.close_client_order_id = current.exit_client_order_id
                        leg.close_order_id = current.exit_order_id
                        leg.close_trade_ids = list(current.exit_trade_ids or [])
                        current.closed_legs.append(leg)
                    current.open_legs = remaining_open
                    current.pending_exit = None
                return self.store.upsert(current)

            return current

    def reconcile_account_symbol(self, account: str, symbol: str, exchange_snapshot: ExchangePositionSnapshot | None) -> RouteControlResult:
        with self.locks.hold(account, symbol):
            local = self.store.get(account, symbol)
            local_positions = [local] if local is not None else []
            exchange_positions = [exchange_snapshot] if exchange_snapshot is not None else []
            alignment = reconcile_positions(local_positions, exchange_positions)
            policy = decide_alignment_policy(alignment)

            if not alignment.ok:
                if policy.action == 'freeze_route':
                    self.routes.freeze(account, symbol, policy.reason)
                if local is not None:
                    local.status = LivePositionStatus.RECONCILE_MISMATCH
                    local.reason = policy.reason
                    self.store.upsert(local)
            else:
                self.routes.enable(account, symbol)

            return RouteControlResult(
                alignment=alignment,
                policy=policy,
                position=self.store.get(account, symbol),
            )

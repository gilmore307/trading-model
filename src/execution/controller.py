from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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

    def submit_entry(self, account: str, symbol: str, route: str, side: str, size: float, entry_order_id: str | None = None) -> LivePosition:
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
            current.size = size
            current.entry_order_id = entry_order_id
            current.reason = 'entry_submitted'
            return self.store.upsert(current)

    def submit_exit(self, account: str, symbol: str, exit_order_id: str | None = None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            current.status = LivePositionStatus.EXIT_SUBMITTED
            current.exit_order_id = exit_order_id
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

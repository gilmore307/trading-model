from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.state.execution_ledger import ExecutionLeg, ExitAllocation, ExitExecution

from src.execution.confirm import verify_entry, verify_exit
from src.execution.locks import AccountSymbolLockRegistry
from src.execution.policy import PolicyDecision, decide_alignment_policy
from src.reconcile.alignment import AlignmentIssueType, AlignmentResult, ExchangePositionSnapshot, reconcile_positions
from src.state.live_position import LivePosition, LivePositionStatus
from src.state.route_registry import RouteRegistry
from src.state.store import LiveStateStore


@dataclass(slots=True)
class RouteControlResult:
    alignment: AlignmentResult
    policy: PolicyDecision
    position: LivePosition | None


class RouteController:
    def __init__(self, store: LiveStateStore | None = None, locks: AccountSymbolLockRegistry | None = None, routes: RouteRegistry | None = None, verification_cycle_timeout: int = 3):
        self.store = store or LiveStateStore()
        self.locks = locks or AccountSymbolLockRegistry()
        self.routes = routes or RouteRegistry()
        self.verification_cycle_timeout = max(1, int(verification_cycle_timeout or 1))

    def _append_event(self, position: LivePosition, event: dict) -> None:
        meta = dict(position.meta or {})
        history = list(meta.get('event_history') or [])
        history.append({**event, 'observed_at': datetime.now(UTC).isoformat()})
        meta['event_history'] = history[-50:]
        position.meta = meta

    def _bump_verification_cycles(self, current: LivePosition, *, phase: str) -> tuple[dict, int]:
        meta = dict(current.meta or {})
        cycles = int(meta.get(f'{phase}_verification_cycles') or 0) + 1
        meta[f'{phase}_verification_cycles'] = cycles
        meta[f'{phase}_verification_last_at'] = datetime.now(UTC).isoformat()
        current.meta = meta
        return meta, cycles

    def _reset_verification_cycles(self, current: LivePosition, *, phase: str) -> dict:
        meta = dict(current.meta or {})
        meta.pop(f'{phase}_verification_cycles', None)
        meta.pop(f'{phase}_verification_last_at', None)
        current.meta = meta
        return meta

    def mark_forced_exit_recovery(self, account: str, symbol: str, *, detail: str | None = None) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            meta = dict(current.meta or {})
            if meta.get('execution_recovery') == 'forced_exit' and meta.get('execution_recovery_detail') == (detail or meta.get('execution_recovery_detail')):
                self._append_event(current, {
                    'kind': 'forced_exit_recovery_duplicate_ignored',
                    'detail': detail,
                })
                current.reason = detail or 'forced_exit_recovery_duplicate_ignored'
                return self.store.upsert(current)
            meta['strategy_stats_eligible'] = 'false'
            meta['strategy_stats_reason'] = 'forced_exit_recovery'
            meta['execution_recovery'] = 'forced_exit'
            if detail is not None:
                meta['execution_recovery_detail'] = detail
            current.meta = meta
            self._append_event(current, {
                'kind': 'forced_exit_recovery_marked',
                'detail': detail,
            })
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
            if current.has_open_leg(execution_id=entry_execution_id, order_id=entry_order_id, client_order_id=entry_client_order_id):
                self._append_event(current, {
                    'kind': 'entry_duplicate_ignored',
                    'execution_id': entry_execution_id,
                    'order_id': entry_order_id,
                    'client_order_id': entry_client_order_id,
                })
                current.reason = 'entry_duplicate_ignored'
                return self.store.upsert(current)
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
            self._reset_verification_cycles(current, phase='entry')
            self._append_event(current, {
                'kind': 'entry_submitted',
                'execution_id': entry_execution_id,
                'order_id': entry_order_id,
                'client_order_id': entry_client_order_id,
                'requested_size': float(size or 0.0),
                'side': side,
            })
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
        requested_size: float | None = None,
    ) -> LivePosition | None:
        with self.locks.hold(account, symbol):
            current = self.store.get(account, symbol)
            if current is None:
                return None
            if current.pending_exit is not None and (
                (exit_execution_id and current.pending_exit.execution_id == exit_execution_id)
                or (exit_order_id and current.pending_exit.order_id == exit_order_id)
                or (exit_client_order_id and current.pending_exit.client_order_id == exit_client_order_id)
            ):
                self._append_event(current, {
                    'kind': 'exit_duplicate_ignored',
                    'execution_id': exit_execution_id,
                    'order_id': exit_order_id,
                    'client_order_id': exit_client_order_id,
                })
                current.reason = 'exit_duplicate_ignored'
                return self.store.upsert(current)
            current.status = LivePositionStatus.EXIT_SUBMITTED
            current.exit_order_id = exit_order_id
            current.exit_execution_id = exit_execution_id
            current.exit_client_order_id = exit_client_order_id
            current.exit_trade_ids = list(exit_trade_ids or [])
            requested_exit_size = float(requested_size if requested_size is not None else (current.ledger_open_size or current.size or 0.0))
            remaining_to_allocate = requested_exit_size
            allocations: list[ExitAllocation] = []
            for leg in current.open_legs:
                if remaining_to_allocate <= 0:
                    break
                alloc_size = min(float(leg.remaining_size or 0.0), remaining_to_allocate)
                if alloc_size <= 0:
                    continue
                allocations.append(ExitAllocation(leg_id=leg.leg_id, requested_size=alloc_size, closed_size=0.0, trade_ids=[], fee_usdt=None, realized_pnl_usdt=None))
                remaining_to_allocate -= alloc_size
            self._reset_verification_cycles(current, phase='exit')
            current.pending_exit = ExitExecution(
                execution_id=exit_execution_id,
                client_order_id=exit_client_order_id,
                order_id=exit_order_id,
                trade_ids=list(exit_trade_ids or []),
                requested_size=requested_exit_size,
                side=current.side,
                status='submitted',
                reason='exit_submitted',
                allocations=allocations,
                submitted_at=datetime.now(UTC),
            )
            self._append_event(current, {
                'kind': 'exit_submitted',
                'execution_id': exit_execution_id,
                'order_id': exit_order_id,
                'client_order_id': exit_client_order_id,
                'requested_size': float(current.pending_exit.requested_size or 0.0),
                'allocation_leg_ids': [a.leg_id for a in allocations],
            })
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

            previous_ledger_size = float(current.ledger_open_size or 0.0)
            previous_side = current.side
            if exchange_snapshot is not None:
                current.side = exchange_snapshot.side
                current.size = float(exchange_snapshot.size or 0.0)
                current.last_exchange_observed_at = datetime.now(UTC)

            if current.open_legs and current.status in {LivePositionStatus.ENTRY_SUBMITTED, LivePositionStatus.ENTRY_VERIFYING} and exchange_snapshot is not None:
                exchange_size = float(exchange_snapshot.size or 0.0)
                baseline = max(0.0, previous_ledger_size - float(current.open_legs[-1].remaining_size or 0.0))
                delta = max(0.0, exchange_size - baseline)
                newest = current.open_legs[-1]
                newest.filled_size = max(float(newest.filled_size or 0.0), delta)
                newest.remaining_size = max(float(newest.remaining_size or 0.0), delta)
                newest.status = 'open'

            if current.pending_exit is not None:
                current.pending_exit.trade_ids = list(current.exit_trade_ids or current.pending_exit.trade_ids or [])
                current.pending_exit.order_id = current.exit_order_id or current.pending_exit.order_id
                if exchange_snapshot is not None:
                    exchange_size = float(exchange_snapshot.size or 0.0)
                    total_before_exit = sum(float(leg.remaining_size or 0.0) for leg in current.open_legs)
                    closed_delta = max(0.0, total_before_exit - exchange_size)
                    alloc_cap = float(current.pending_exit.requested_size or 0.0)
                    already_closed = sum(float(a.closed_size or 0.0) for a in current.pending_exit.allocations)
                    remaining_to_apply = min(closed_delta, max(0.0, alloc_cap - already_closed))
                    updated_open_legs = []
                    pending_trade_ids = list(current.pending_exit.trade_ids or [])
                    exit_fee_total = None if not isinstance((current.meta or {}).get('last_exit_fee_usdt'), (int, float)) else float((current.meta or {}).get('last_exit_fee_usdt'))
                    exit_realized_total = None if not isinstance((current.meta or {}).get('last_exit_realized_pnl_usdt'), (int, float)) else float((current.meta or {}).get('last_exit_realized_pnl_usdt'))
                    for leg in current.open_legs:
                        leg_remaining = float(leg.remaining_size or 0.0)
                        if remaining_to_apply > 0.0:
                            consume = min(leg_remaining, remaining_to_apply)
                            leg.remaining_size = leg_remaining - consume
                            remaining_to_apply -= consume
                            for alloc in current.pending_exit.allocations:
                                if alloc.leg_id == leg.leg_id:
                                    alloc.closed_size = min(alloc.requested_size, float(alloc.closed_size or 0.0) + consume)
                                    alloc.trade_ids = list(dict.fromkeys([*(alloc.trade_ids or []), *pending_trade_ids]))
                                    ratio = 0.0 if not current.pending_exit.requested_size else float(consume) / float(current.pending_exit.requested_size)
                                    if exit_fee_total is not None:
                                        alloc.fee_usdt = round(float(exit_fee_total) * ratio, 12)
                                    if exit_realized_total is not None:
                                        alloc.realized_pnl_usdt = round(float(exit_realized_total) * ratio, 12)
                                    break
                        if float(leg.remaining_size or 0.0) <= 1e-12:
                            leg.remaining_size = 0.0
                            leg.status = 'closed'
                            leg.closed_at = datetime.now(UTC)
                            leg.close_execution_id = current.exit_execution_id
                            leg.close_client_order_id = current.exit_client_order_id
                            leg.close_order_id = current.exit_order_id
                            leg.close_trade_ids = list(current.exit_trade_ids or [])
                            current.closed_legs.append(leg)
                        else:
                            updated_open_legs.append(leg)
                    current.open_legs = updated_open_legs
                    total_alloc_closed = sum(float(a.closed_size or 0.0) for a in current.pending_exit.allocations)
                    if total_alloc_closed >= float(current.pending_exit.requested_size or 0.0) - 1e-12:
                        current.pending_exit.status = 'closed'
                    elif total_alloc_closed > 0:
                        current.pending_exit.status = 'partial'

            if current.status in {LivePositionStatus.ENTRY_SUBMITTED, LivePositionStatus.ENTRY_VERIFYING}:
                meta, cycles = self._bump_verification_cycles(current, phase='entry')
                decision = verify_entry(current, exchange_snapshot)
                if not decision.accepted and cycles >= self.verification_cycle_timeout:
                    decision = type(decision)(
                        next_status=LivePositionStatus.FLAT,
                        accepted=False,
                        reason='entry_verification_timeout',
                    )
                    meta['strategy_stats_eligible'] = 'false'
                    meta['strategy_stats_reason'] = 'missed_entry'
                    meta['execution_recovery'] = 'missed_entry'
                    meta['execution_recovery_detail'] = 'entry_verification_timeout'
                    current.meta = meta
                    current.side = None
                    current.size = 0.0
                    current.open_legs = []
                    current.entry_trade_ids = []
                    self.routes.enable(account, symbol)
                current.status = decision.next_status
                current.reason = decision.reason
                if decision.accepted:
                    self._reset_verification_cycles(current, phase='entry')
                self._append_event(current, {
                    'kind': 'entry_verification',
                    'accepted': decision.accepted,
                    'next_status': decision.next_status.value,
                    'reason': decision.reason,
                    'exchange_size': None if exchange_snapshot is None else float(exchange_snapshot.size or 0.0),
                    'verification_cycles': cycles,
                })
                return self.store.upsert(current)

            if current.status in {LivePositionStatus.EXIT_SUBMITTED, LivePositionStatus.EXIT_VERIFYING}:
                meta, cycles = self._bump_verification_cycles(current, phase='exit')
                decision = verify_exit(current, exchange_snapshot)
                if not decision.accepted and cycles >= self.verification_cycle_timeout:
                    meta['strategy_stats_eligible'] = 'false'
                    meta['strategy_stats_reason'] = 'forced_exit_recovery'
                    meta['execution_recovery'] = 'forced_exit'
                    meta['execution_recovery_detail'] = 'exit_verification_timeout'
                    current.meta = meta
                    current.reason = 'exit_verification_timeout'
                    self._append_event(current, {
                        'kind': 'exit_verification_timeout',
                        'verification_cycles': cycles,
                        'exchange_size': None if exchange_snapshot is None else float(exchange_snapshot.size or 0.0),
                    })
                current.status = decision.next_status
                current.reason = decision.reason if decision.accepted or cycles < self.verification_cycle_timeout else 'exit_verification_timeout'
                if decision.accepted:
                    self._reset_verification_cycles(current, phase='exit')
                self._append_event(current, {
                    'kind': 'exit_verification',
                    'accepted': decision.accepted,
                    'next_status': decision.next_status.value,
                    'reason': current.reason,
                    'exchange_size': None if exchange_snapshot is None else float(exchange_snapshot.size or 0.0),
                    'verification_cycles': cycles,
                })
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
                return self.store.upsert(current)

            return current

    def reconcile_account_symbol(self, account: str, symbol: str, exchange_snapshot: ExchangePositionSnapshot | None) -> RouteControlResult:
        with self.locks.hold(account, symbol):
            local = self.store.get(account, symbol)
            local_positions = [local] if local is not None else []
            exchange_positions = [exchange_snapshot] if exchange_snapshot is not None else []
            alignment = reconcile_positions(local_positions, exchange_positions)

            verification_grace = False
            if local is not None and local.status in {LivePositionStatus.ENTRY_SUBMITTED, LivePositionStatus.ENTRY_VERIFYING}:
                cycles = int((local.meta or {}).get('entry_verification_cycles') or 0)
                if cycles < self.verification_cycle_timeout:
                    filtered = [issue for issue in alignment.issues if issue.type not in {AlignmentIssueType.MISSING_EXCHANGE_POSITION, AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION, AlignmentIssueType.SIZE_MISMATCH}]
                    verification_grace = len(filtered) != len(alignment.issues)
                    alignment = AlignmentResult(ok=not filtered, issues=filtered)
            elif local is not None and local.status in {LivePositionStatus.EXIT_SUBMITTED, LivePositionStatus.EXIT_VERIFYING}:
                cycles = int((local.meta or {}).get('exit_verification_cycles') or 0)
                if cycles < self.verification_cycle_timeout:
                    filtered = [issue for issue in alignment.issues if issue.type not in {AlignmentIssueType.MISSING_EXCHANGE_POSITION, AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION, AlignmentIssueType.SIZE_MISMATCH}]
                    verification_grace = len(filtered) != len(alignment.issues)
                    alignment = AlignmentResult(ok=not filtered, issues=filtered)

            policy = decide_alignment_policy(alignment)
            if verification_grace and alignment.ok and local is not None:
                policy = PolicyDecision(trade_enabled=False, action='verify_only', reason='verification_grace_window')

            if not alignment.ok:
                if policy.action == 'freeze_route':
                    self.routes.freeze(account, symbol, policy.reason)
                if local is not None:
                    local.status = LivePositionStatus.RECONCILE_MISMATCH
                    local.reason = policy.reason
                    self._append_event(local, {
                        'kind': 'reconcile_failed',
                        'policy_action': policy.action,
                        'policy_reason': policy.reason,
                        'issue_types': [issue.type.value for issue in alignment.issues],
                        'verification_grace': verification_grace,
                    })
                    self.store.upsert(local)
            else:
                self.routes.enable(account, symbol)
                if local is not None:
                    self._append_event(local, {
                        'kind': 'reconcile_ok',
                        'policy_action': policy.action,
                        'policy_reason': policy.reason,
                        'verification_grace': verification_grace,
                    })
                    self.store.upsert(local)

            return RouteControlResult(
                alignment=alignment,
                policy=policy,
                position=self.store.get(account, symbol),
            )

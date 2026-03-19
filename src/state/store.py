from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from src.state.execution_ledger import ExecutionLeg, ExitAllocation, ExitExecution
from src.state.live_position import LivePosition, LivePositionStatus

STATE_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/live-state-store.json')


def _dt(value):
    return datetime.fromisoformat(value) if value else None


def _leg_from_dict(item: dict) -> ExecutionLeg:
    return ExecutionLeg(
        leg_id=item['leg_id'],
        execution_id=item.get('execution_id'),
        client_order_id=item.get('client_order_id'),
        order_id=item.get('order_id'),
        trade_ids=list(item.get('trade_ids') or []),
        action=item.get('action', 'entry'),
        side=item.get('side'),
        requested_size=float(item.get('requested_size') or 0.0),
        filled_size=float(item.get('filled_size') or 0.0),
        remaining_size=float(item.get('remaining_size') or 0.0),
        status=item.get('status', 'open'),
        reason=item.get('reason'),
        opened_at=_dt(item.get('opened_at')),
        closed_at=_dt(item.get('closed_at')),
        close_execution_id=item.get('close_execution_id'),
        close_client_order_id=item.get('close_client_order_id'),
        close_order_id=item.get('close_order_id'),
        close_trade_ids=list(item.get('close_trade_ids') or []),
    )


def _exit_from_dict(item: dict | None) -> ExitExecution | None:
    if not item:
        return None
    return ExitExecution(
        execution_id=item.get('execution_id'),
        client_order_id=item.get('client_order_id'),
        order_id=item.get('order_id'),
        trade_ids=list(item.get('trade_ids') or []),
        requested_size=float(item.get('requested_size') or 0.0),
        side=item.get('side'),
        status=item.get('status', 'submitted'),
        reason=item.get('reason'),
        submitted_at=_dt(item.get('submitted_at')),
        allocations=[
            ExitAllocation(
                leg_id=row['leg_id'],
                requested_size=float(row.get('requested_size') or 0.0),
                closed_size=float(row.get('closed_size') or 0.0),
            )
            for row in (item.get('allocations') or [])
            if isinstance(row, dict) and row.get('leg_id')
        ],
    )


class LiveStateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or STATE_PATH
        self._positions: dict[tuple[str, str], LivePosition] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return
        for item in payload.get('positions', []):
            try:
                position = LivePosition(
                    account=item['account'],
                    symbol=item['symbol'],
                    route=item['route'],
                    status=LivePositionStatus(item.get('status', LivePositionStatus.FLAT.value)),
                    side=item.get('side'),
                    size=float(item.get('size') or 0.0),
                    entry_order_id=item.get('entry_order_id'),
                    exit_order_id=item.get('exit_order_id'),
                    entry_execution_id=item.get('entry_execution_id'),
                    exit_execution_id=item.get('exit_execution_id'),
                    entry_client_order_id=item.get('entry_client_order_id'),
                    exit_client_order_id=item.get('exit_client_order_id'),
                    entry_trade_ids=item.get('entry_trade_ids'),
                    exit_trade_ids=item.get('exit_trade_ids'),
                    open_legs=[_leg_from_dict(row) for row in (item.get('open_legs') or []) if isinstance(row, dict) and row.get('leg_id')],
                    closed_legs=[_leg_from_dict(row) for row in (item.get('closed_legs') or []) if isinstance(row, dict) and row.get('leg_id')],
                    pending_exit=_exit_from_dict(item.get('pending_exit')),
                    last_exchange_observed_at=datetime.fromisoformat(item['last_exchange_observed_at']) if item.get('last_exchange_observed_at') else None,
                    last_local_updated_at=datetime.fromisoformat(item['last_local_updated_at']) if item.get('last_local_updated_at') else None,
                    reason=item.get('reason'),
                    meta=item.get('meta') or {},
                )
            except Exception:
                continue
            self._positions[self.key(position.account, position.symbol)] = position

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'positions': [
                {
                    **asdict(position),
                    'status': position.status.value,
                    'last_exchange_observed_at': position.last_exchange_observed_at.astimezone(UTC).isoformat() if position.last_exchange_observed_at else None,
                    'last_local_updated_at': position.last_local_updated_at.astimezone(UTC).isoformat() if position.last_local_updated_at else None,
                }
                for position in self._positions.values()
            ]
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=lambda v: v.astimezone(UTC).isoformat() if isinstance(v, datetime) else str(v)), encoding='utf-8')

    def key(self, account: str, symbol: str) -> tuple[str, str]:
        return (account, symbol)

    def get(self, account: str, symbol: str) -> LivePosition | None:
        return self._positions.get(self.key(account, symbol))

    def upsert(self, position: LivePosition) -> LivePosition:
        position.last_local_updated_at = datetime.now(UTC)
        self._positions[self.key(position.account, position.symbol)] = position
        self._save()
        return position

    def list_positions(self) -> list[LivePosition]:
        return list(self._positions.values())

    def patch(self, account: str, symbol: str, **changes) -> LivePosition | None:
        current = self.get(account, symbol)
        if current is None:
            return None
        updated = replace(current, **changes)
        updated.last_local_updated_at = datetime.now(UTC)
        self._positions[self.key(account, symbol)] = updated
        self._save()
        return updated

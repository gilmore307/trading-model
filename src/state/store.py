from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from src.state.live_position import LivePosition, LivePositionStatus

STATE_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/live-state-store.json')


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
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

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

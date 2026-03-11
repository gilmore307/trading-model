from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from src.state.live_position import LivePosition


class LiveStateStore:
    def __init__(self):
        self._positions: dict[tuple[str, str], LivePosition] = {}

    def key(self, account: str, symbol: str) -> tuple[str, str]:
        return (account, symbol)

    def get(self, account: str, symbol: str) -> LivePosition | None:
        return self._positions.get(self.key(account, symbol))

    def upsert(self, position: LivePosition) -> LivePosition:
        position.last_local_updated_at = datetime.now(UTC)
        self._positions[self.key(position.account, position.symbol)] = position
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
        return updated

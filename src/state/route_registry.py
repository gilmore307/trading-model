from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class RouteState:
    account: str
    symbol: str
    enabled: bool = True
    frozen_reason: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RouteRegistry:
    def __init__(self):
        self._routes: dict[tuple[str, str], RouteState] = {}

    def key(self, account: str, symbol: str) -> tuple[str, str]:
        return (account, symbol)

    def get(self, account: str, symbol: str) -> RouteState:
        key = self.key(account, symbol)
        if key not in self._routes:
            self._routes[key] = RouteState(account=account, symbol=symbol)
        return self._routes[key]

    def freeze(self, account: str, symbol: str, reason: str) -> RouteState:
        state = self.get(account, symbol)
        state.enabled = False
        state.frozen_reason = reason
        state.updated_at = datetime.now(UTC)
        return state

    def enable(self, account: str, symbol: str) -> RouteState:
        state = self.get(account, symbol)
        state.enabled = True
        state.frozen_reason = None
        state.updated_at = datetime.now(UTC)
        return state

    def is_enabled(self, account: str, symbol: str) -> bool:
        return self.get(account, symbol).enabled

    def list_routes(self) -> list[RouteState]:
        return list(self._routes.values())

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROUTE_STATE_PATH = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime/route-registry.json')


@dataclass(slots=True)
class RouteState:
    account: str
    symbol: str
    enabled: bool = True
    frozen_reason: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RouteRegistry:
    def __init__(self, path: Path | None = None):
        self.path = path or ROUTE_STATE_PATH
        self._routes: dict[tuple[str, str], RouteState] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return
        for item in payload.get('routes', []):
            try:
                state = RouteState(
                    account=item['account'],
                    symbol=item['symbol'],
                    enabled=bool(item.get('enabled', True)),
                    frozen_reason=item.get('frozen_reason'),
                    updated_at=datetime.fromisoformat(item['updated_at']) if item.get('updated_at') else datetime.now(UTC),
                )
            except Exception:
                continue
            self._routes[self.key(state.account, state.symbol)] = state

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'routes': [
                {
                    **asdict(state),
                    'updated_at': state.updated_at.astimezone(UTC).isoformat(),
                }
                for state in self._routes.values()
            ]
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def key(self, account: str, symbol: str) -> tuple[str, str]:
        return (account, symbol)

    def get(self, account: str, symbol: str) -> RouteState:
        key = self.key(account, symbol)
        if key not in self._routes:
            self._routes[key] = RouteState(account=account, symbol=symbol)
            self._save()
        return self._routes[key]

    def freeze(self, account: str, symbol: str, reason: str) -> RouteState:
        state = self.get(account, symbol)
        state.enabled = False
        state.frozen_reason = reason
        state.updated_at = datetime.now(UTC)
        self._save()
        return state

    def enable(self, account: str, symbol: str) -> RouteState:
        state = self.get(account, symbol)
        state.enabled = True
        state.frozen_reason = None
        state.updated_at = datetime.now(UTC)
        self._save()
        return state

    def is_enabled(self, account: str, symbol: str) -> bool:
        return self.get(account, symbol).enabled

    def list_routes(self) -> list[RouteState]:
        return list(self._routes.values())

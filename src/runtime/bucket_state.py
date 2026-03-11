from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class BucketState:
    account: str
    symbol: str
    capital_usdt: float
    allocated_usdt: float = 0.0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class BucketStateStore:
    def __init__(self):
        self._buckets: dict[tuple[str, str], BucketState] = {}

    def reset_bucket(self, account: str, symbol: str, capital_usdt: float) -> BucketState:
        state = BucketState(account=account, symbol=symbol, capital_usdt=capital_usdt)
        self._buckets[(account, symbol)] = state
        return state

    def get(self, account: str, symbol: str) -> BucketState | None:
        return self._buckets.get((account, symbol))

    def list(self) -> list[BucketState]:
        return list(self._buckets.values())

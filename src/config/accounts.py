from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategyAccount:
    alias: str
    label: str


V2_ACCOUNTS: tuple[StrategyAccount, ...] = (
    StrategyAccount(alias="trend", label="Trend"),
    StrategyAccount(alias="meanrev", label="Meanrev"),
    StrategyAccount(alias="compression", label="Compression"),
    StrategyAccount(alias="crowded", label="Crowded"),
    StrategyAccount(alias="realtime", label="Realtime"),
)

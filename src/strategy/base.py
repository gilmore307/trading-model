from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

SignalSide = Literal["long", "short", "flat"]


@dataclass
class Signal:
    symbol: str
    strategy: str
    side: SignalSide
    reason: str


class Strategy(Protocol):
    name: str

    def evaluate(self, symbol: str, candles: list[list[float]]) -> Signal:
        ...

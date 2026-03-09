from __future__ import annotations

from src.strategy.base import Signal


class BreakoutStrategy:
    name = "breakout"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def evaluate(self, symbol: str, candles: list[list[float]]) -> Signal:
        if len(candles) < self.lookback + 1:
            return Signal(symbol=symbol, strategy=self.name, side="flat", reason="not_enough_data")

        highs = [c[2] for c in candles[-self.lookback - 1 : -1]]
        lows = [c[3] for c in candles[-self.lookback - 1 : -1]]
        close = candles[-1][4]

        if close > max(highs):
            return Signal(symbol=symbol, strategy=self.name, side="long", reason="breakout_high")
        if close < min(lows):
            return Signal(symbol=symbol, strategy=self.name, side="short", reason="breakout_low")
        return Signal(symbol=symbol, strategy=self.name, side="flat", reason="no_breakout")

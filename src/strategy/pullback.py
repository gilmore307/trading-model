from __future__ import annotations

from src.strategy.base import Signal


class PullbackStrategy:
    name = "pullback"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def evaluate(self, symbol: str, candles: list[list[float]]) -> Signal:
        if len(candles) < self.lookback + 2:
            return Signal(symbol=symbol, strategy=self.name, side="flat", reason="not_enough_data")

        closes = [c[4] for c in candles[-self.lookback - 1 :]]
        recent_high = max(c[2] for c in candles[-self.lookback - 1 : -1])
        recent_low = min(c[3] for c in candles[-self.lookback - 1 : -1])
        close = closes[-1]
        prev_close = closes[-2]
        mean_close = sum(closes[:-1]) / max(1, len(closes) - 1)

        if prev_close >= mean_close and close < mean_close and close > recent_low:
            return Signal(symbol=symbol, strategy=self.name, side="long", reason="pullback_to_mean")
        if prev_close <= mean_close and close > mean_close and close < recent_high:
            return Signal(symbol=symbol, strategy=self.name, side="short", reason="pullback_reject_mean")
        return Signal(symbol=symbol, strategy=self.name, side="flat", reason="no_pullback")

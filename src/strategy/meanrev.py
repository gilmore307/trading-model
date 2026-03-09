from __future__ import annotations

from src.strategy.base import Signal


class MeanReversionStrategy:
    name = "meanrev"

    def __init__(self, lookback: int = 20, threshold: float = 0.015):
        self.lookback = lookback
        self.threshold = threshold

    def evaluate(self, symbol: str, candles: list[list[float]]) -> Signal:
        if len(candles) < self.lookback:
            return Signal(symbol=symbol, strategy=self.name, side="flat", reason="not_enough_data")

        closes = [c[4] for c in candles[-self.lookback :]]
        close = closes[-1]
        mean_close = sum(closes[:-1]) / max(1, len(closes) - 1)
        if mean_close <= 0:
            return Signal(symbol=symbol, strategy=self.name, side="flat", reason="invalid_mean")

        deviation = (close - mean_close) / mean_close
        if deviation <= -self.threshold:
            return Signal(symbol=symbol, strategy=self.name, side="long", reason="meanrev_oversold")
        if deviation >= self.threshold:
            return Signal(symbol=symbol, strategy=self.name, side="short", reason="meanrev_overbought")
        return Signal(symbol=symbol, strategy=self.name, side="flat", reason="no_meanrev")

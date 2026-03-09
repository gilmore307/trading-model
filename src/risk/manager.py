from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    reason: str


class RiskManager:
    def __init__(self, max_open_positions: int = 2, signal_cooldown_bars: int = 12):
        self.max_open_positions = max_open_positions
        self.signal_cooldown_bars = signal_cooldown_bars

    def allow_entry(self, snapshot: dict, position_key: str, side: str, bar_id: int, notional_usdt: float) -> RiskDecision:
        if side == "flat":
            return RiskDecision(False, "flat_signal")

        buckets = snapshot.get("buckets", {})
        bucket = buckets.get(position_key, {})
        available_usdt = float(bucket.get("available_usdt", bucket.get("initial_capital_usdt", 0.0)))
        initial_capital_usdt = float(bucket.get("initial_capital_usdt", 0.0))
        realized_pnl_usdt = float(bucket.get("realized_pnl_usdt", 0.0))
        fees_usdt = float(bucket.get("fees_usdt", 0.0))
        equity_usdt = available_usdt + float(bucket.get("allocated_usdt", 0.0)) + realized_pnl_usdt - fees_usdt
        if initial_capital_usdt > 0 and equity_usdt <= initial_capital_usdt * 0.5:
            return RiskDecision(False, f"bucket_eliminated_50pct_drawdown:{position_key}:{equity_usdt}")

        if available_usdt < notional_usdt:
            return RiskDecision(False, f"bucket_insufficient_capital:{position_key}:{available_usdt}")

        last_signals = snapshot.get("last_signals", {})
        last_signal = last_signals.get(position_key)
        if last_signal and last_signal.get("side") == side:
            last_bar_id = int(last_signal.get("bar_id", -10**9))
            bars_since = bar_id - last_bar_id
            if bars_since < self.signal_cooldown_bars:
                return RiskDecision(False, f"signal_cooldown:{position_key}:{side}:{bars_since}")

        return RiskDecision(True, "ok")

    def dynamic_leverage(self, symbol: str, signal_side: str, candles: list[list[float]]) -> int:
        if len(candles) < 10:
            return 3

        closes = [float(c[4]) for c in candles[-10:]]
        highs = [float(c[2]) for c in candles[-10:]]
        lows = [float(c[3]) for c in candles[-10:]]
        latest_close = closes[-1]
        if latest_close <= 0:
            return 3

        range_ratio = (max(highs) - min(lows)) / latest_close
        momentum = abs(closes[-1] - closes[0]) / latest_close

        leverage = 3
        if range_ratio < 0.01 and momentum > 0.006:
            leverage = 12
        elif range_ratio < 0.015 and momentum > 0.004:
            leverage = 8
        elif range_ratio < 0.025:
            leverage = 5

        if symbol.startswith("SOL"):
            leverage = min(leverage, 10)
        if symbol.startswith("BTC"):
            leverage = min(max(leverage, 4), 20)
        else:
            leverage = min(max(leverage, 3), 20)

        return max(3, min(leverage, 20))

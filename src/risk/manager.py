from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskDecision:
    allowed: bool
    reason: str


@dataclass
class SizingPlan:
    risk_budget_usdt: float
    stop_distance_ratio: float
    stop_distance_usdt: float
    effective_notional_usdt: float
    capped_notional_usdt: float
    leverage: int
    margin_required_usdt: float
    entry_price: float


class RiskManager:
    def __init__(
        self,
        max_open_positions: int = 2,
        signal_cooldown_bars: int = 12,
        risk_per_trade_fraction: float = 0.01,
        min_stop_distance_ratio: float = 0.003,
        atr_lookback: int = 14,
        stop_atr_multiple: float = 1.5,
    ):
        self.max_open_positions = max_open_positions
        self.signal_cooldown_bars = signal_cooldown_bars
        self.risk_per_trade_fraction = risk_per_trade_fraction
        self.min_stop_distance_ratio = min_stop_distance_ratio
        self.atr_lookback = atr_lookback
        self.stop_atr_multiple = stop_atr_multiple

    def allow_entry(self, snapshot: dict, position_key: str, side: str, bar_id: int, notional_usdt: float) -> RiskDecision:
        if side == "flat":
            return RiskDecision(False, "flat_signal")

        buckets = snapshot.get("buckets", {})
        bucket = buckets.get(position_key, {})
        available_usdt = float(bucket.get("available_usdt", bucket.get("initial_capital_usdt", 0.0)))
        initial_capital_usdt = float(bucket.get("initial_capital_usdt", 0.0))
        realized_pnl_usdt = float(bucket.get("realized_pnl_usdt") or 0.0)
        fees_usdt = float(bucket.get("fees_usdt") or 0.0)
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

    def estimate_stop_distance_ratio(self, candles: list[list[float]]) -> float:
        if len(candles) < 2:
            return self.min_stop_distance_ratio

        recent = candles[-self.atr_lookback :]
        true_ranges = []
        prev_close = float(recent[0][4])
        for candle in recent:
            high = float(candle[2])
            low = float(candle[3])
            close = float(candle[4])
            true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(true_range)
            prev_close = close

        last_close = float(recent[-1][4])
        if last_close <= 0:
            return self.min_stop_distance_ratio

        atr = sum(true_ranges) / max(1, len(true_ranges))
        atr_ratio = atr / last_close
        return max(self.min_stop_distance_ratio, atr_ratio * self.stop_atr_multiple)

    def bucket_equity_usdt(self, bucket: dict) -> float:
        available_usdt = float(bucket.get("available_usdt", bucket.get("initial_capital_usdt", 0.0)))
        allocated_usdt = float(bucket.get("allocated_usdt", 0.0))
        realized_pnl_usdt = float(bucket.get("realized_pnl_usdt") or 0.0)
        fees_usdt = float(bucket.get("fees_usdt") or 0.0)
        return available_usdt + allocated_usdt + realized_pnl_usdt - fees_usdt

    def plan_entry_size(self, *, bucket: dict, candles: list[list[float]], leverage: int) -> SizingPlan:
        equity_usdt = max(0.0, self.bucket_equity_usdt(bucket))
        available_usdt = float(bucket.get("available_usdt", 0.0))
        entry_price = float(candles[-1][4]) if candles else 0.0
        if entry_price <= 0:
            raise RuntimeError("Cannot size entry: invalid entry price")

        stop_distance_ratio = self.estimate_stop_distance_ratio(candles)
        stop_distance_usdt = entry_price * stop_distance_ratio
        if stop_distance_usdt <= 0:
            raise RuntimeError("Cannot size entry: invalid stop distance")

        risk_budget_usdt = equity_usdt * self.risk_per_trade_fraction
        effective_notional_usdt = risk_budget_usdt / stop_distance_ratio
        capped_notional_usdt = min(effective_notional_usdt, available_usdt * leverage)
        margin_required_usdt = 0.0 if leverage <= 0 else capped_notional_usdt / leverage

        return SizingPlan(
            risk_budget_usdt=risk_budget_usdt,
            stop_distance_ratio=stop_distance_ratio,
            stop_distance_usdt=stop_distance_usdt,
            effective_notional_usdt=effective_notional_usdt,
            capped_notional_usdt=capped_notional_usdt,
            leverage=leverage,
            margin_required_usdt=margin_required_usdt,
            entry_price=entry_price,
        )

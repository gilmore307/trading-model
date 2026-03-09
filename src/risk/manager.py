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

        positions = snapshot.get("positions", {})
        position = positions.get(position_key)
        if position and position.get("status") == "open":
            if position.get("side") == side:
                return RiskDecision(False, f"position_already_open:{position_key}:{side}")
            return RiskDecision(False, f"opposite_position_open:{position_key}:{position.get('side')}")

        open_positions = sum(1 for item in positions.values() if item.get("status") == "open")
        if open_positions >= self.max_open_positions:
            return RiskDecision(False, f"max_open_positions_reached:{position_key}")

        buckets = snapshot.get("buckets", {})
        bucket = buckets.get(position_key, {})
        available_usdt = float(bucket.get("available_usdt", bucket.get("initial_capital_usdt", 0.0)))
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

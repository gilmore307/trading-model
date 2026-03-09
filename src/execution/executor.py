from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionResult:
    submitted: bool
    mode: str
    detail: str
    state_patch: dict
    venue_response: dict[str, Any] | None = None


class DemoExecutor:
    def __init__(self, armed: bool = False, client: Any | None = None):
        self.armed = armed
        self.client = client

    def submit_entry_signal(
        self,
        *,
        position_key: str,
        symbol: str,
        strategy: str,
        side: str,
        reason: str,
        bar_id: int,
        order_size_usdt: float,
        bucket: dict,
    ) -> ExecutionResult:
        venue_response = None
        mode = "dry_run"
        submitted = False
        if self.armed:
            if self.client is None:
                raise RuntimeError("Executor is armed but no exchange client was supplied.")
            venue_response = self.client.create_entry_order(symbol, side, order_size_usdt)
            mode = "demo_submit"
            submitted = True

        position = {
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": side,
            "reason": reason,
            "entry_bar_id": bar_id,
            "notional_usdt": order_size_usdt,
            "status": "open",
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
            "venue_status": None if venue_response is None else venue_response.get("status"),
            "amount": None if venue_response is None else venue_response.get("amount"),
            "reference_price": None if venue_response is None else venue_response.get("reference_price"),
        }
        event = {
            "type": "entry",
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": side,
            "reason": reason,
            "bar_id": bar_id,
            "mode": mode,
            "notional_usdt": order_size_usdt,
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
        }
        state_patch = {
            "positions": {position_key: position},
            "last_signals": {
                position_key: {
                    "side": side,
                    "reason": reason,
                    "bar_id": bar_id,
                }
            },
            "buckets": {
                position_key: {
                    **bucket,
                    "available_usdt": float(bucket.get("available_usdt", 0.0)) - order_size_usdt,
                    "allocated_usdt": float(bucket.get("allocated_usdt", 0.0)) + order_size_usdt,
                }
            },
            "history_append": [event],
        }
        return ExecutionResult(
            submitted=submitted,
            mode=mode,
            detail=f"entry:{position_key}:{side}:{reason}:{bar_id}",
            state_patch=state_patch,
            venue_response=venue_response,
        )

    def submit_exit_signal(
        self,
        *,
        position_key: str,
        symbol: str,
        strategy: str,
        position: dict,
        reason: str,
        bar_id: int,
        bucket: dict,
    ) -> ExecutionResult:
        venue_response = None
        mode = "dry_run"
        submitted = False
        if self.armed:
            if self.client is None:
                raise RuntimeError("Executor is armed but no exchange client was supplied.")
            venue_response = self.client.create_exit_order(symbol, position.get("side", "long"), float(position.get("amount") or 0.0))
            mode = "demo_submit"
            submitted = True

        released_usdt = float(position.get("notional_usdt") or 0.0)
        closed_position = {
            **position,
            "status": "closed",
            "exit_bar_id": bar_id,
            "exit_reason": reason,
            "exit_order_id": None if venue_response is None else venue_response.get("order_id"),
            "exit_status": None if venue_response is None else venue_response.get("status"),
        }
        event = {
            "type": "exit",
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": position.get("side"),
            "reason": reason,
            "bar_id": bar_id,
            "mode": mode,
            "released_usdt": released_usdt,
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
        }
        state_patch = {
            "positions": {position_key: closed_position},
            "last_signals": {
                position_key: {
                    "side": "flat",
                    "reason": reason,
                    "bar_id": bar_id,
                }
            },
            "buckets": {
                position_key: {
                    **bucket,
                    "available_usdt": float(bucket.get("available_usdt", 0.0)) + released_usdt,
                    "allocated_usdt": max(0.0, float(bucket.get("allocated_usdt", 0.0)) - released_usdt),
                }
            },
            "history_append": [event],
        }
        return ExecutionResult(
            submitted=submitted,
            mode=mode,
            detail=f"exit:{position_key}:{reason}:{bar_id}",
            state_patch=state_patch,
            venue_response=venue_response,
        )

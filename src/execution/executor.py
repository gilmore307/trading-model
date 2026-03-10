from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime, UTC


def realized_pnl_from_prices(side: str | None, amount: float | None, entry_price: float | None, exit_price: float | None) -> float | None:
    try:
        qty = float(amount or 0.0)
        entry = float(entry_price or 0.0)
        exit_ = float(exit_price or 0.0)
    except Exception:
        return None
    if qty <= 0 or entry <= 0 or exit_ <= 0:
        return None
    if side == 'long':
        return (exit_ - entry) * qty
    if side == 'short':
        return (entry - exit_) * qty
    return None


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

    def _make_trade_id(self, position_key: str, bar_id: int, existing_positions: list[dict]) -> str:
        ts = datetime.fromtimestamp(int(bar_id) / 1000, tz=UTC).strftime('%Y%m%dT%H%M%SZ')
        seq = len(existing_positions) + 1
        return f"{position_key}:{ts}:{seq:04d}"

    def _make_event_id(self, trade_id: str, event_type: str, bar_id: int) -> str:
        return f"{trade_id}:{event_type}:{bar_id}"

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
        margin_required_usdt: float,
        leverage: int,
        bucket: dict,
        existing_positions: list[dict],
        current_open_amount: float = 0.0,
    ) -> ExecutionResult:
        venue_response = None
        mode = "dry_run"
        submitted = False
        if self.armed:
            if self.client is None:
                raise RuntimeError("Executor is armed but no exchange client was supplied.")
            venue_response = self.client.create_entry_order(symbol, side, order_size_usdt, current_open_amount=current_open_amount)
            mode = "demo_submit"
            submitted = True

        verified_entry = True if venue_response is None else bool(venue_response.get("verified_entry", False))
        trade_id = self._make_trade_id(position_key, bar_id, existing_positions)
        position = {
            "trade_id": trade_id,
            "entry_id": f"{position_key}:{bar_id}:{len(existing_positions)+1}",
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": side,
            "reason": reason,
            "entry_bar_id": bar_id,
            "notional_usdt": order_size_usdt,
            "margin_required_usdt": margin_required_usdt,
            "leverage": leverage,
            "status": "open" if (venue_response is None or verified_entry) else "entry_incomplete",
            "account_alias": None if self.client is None else getattr(self.client, "account_alias", None),
            "account_label": None if self.client is None else getattr(self.client, "account_label", None),
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
            "venue_status": None if venue_response is None else venue_response.get("status"),
            "venue_order_side": None if venue_response is None else venue_response.get("order_side"),
            "venue_ccxt_symbol": None if venue_response is None else venue_response.get("ccxt_symbol"),
            "requested_notional_usdt": None if venue_response is None else venue_response.get("notional_usdt"),
            "amount": None if venue_response is None else venue_response.get("amount"),
            "requested_amount": None if venue_response is None else venue_response.get("amount"),
            "reference_price": None if venue_response is None else venue_response.get("reference_price"),
            "fee_usdt": None if venue_response is None else venue_response.get("fee_usdt"),
            "fee_ccy": None if venue_response is None else venue_response.get("fee_ccy"),
            "fee_rate": None if venue_response is None else venue_response.get("fee_rate"),
            "fill_ids": None if venue_response is None else venue_response.get("fill_ids"),
            "fill_count": None if venue_response is None else venue_response.get("fill_count"),
            "entry_verified": verified_entry if venue_response is not None else None,
            "entry_live_contracts": None if venue_response is None else venue_response.get("live_contracts"),
            "entry_live_side": None if venue_response is None else venue_response.get("live_side"),
        }
        event = {
            "event_id": self._make_event_id(trade_id, "entry", bar_id),
            "trade_id": trade_id,
            "type": "entry",
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": side,
            "reason": reason,
            "bar_id": bar_id,
            "mode": mode,
            "account_alias": None if self.client is None else getattr(self.client, "account_alias", None),
            "account_label": None if self.client is None else getattr(self.client, "account_label", None),
            "notional_usdt": order_size_usdt,
            "margin_required_usdt": margin_required_usdt,
            "leverage": leverage,
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
            "venue_status": None if venue_response is None else venue_response.get("status"),
            "venue_order_side": None if venue_response is None else venue_response.get("order_side"),
            "venue_ccxt_symbol": None if venue_response is None else venue_response.get("ccxt_symbol"),
            "requested_notional_usdt": None if venue_response is None else venue_response.get("notional_usdt"),
            "executed_amount": None if venue_response is None else venue_response.get("amount"),
            "reference_price": None if venue_response is None else venue_response.get("reference_price"),
            "fee_usdt": None if venue_response is None else venue_response.get("fee_usdt"),
            "fee_ccy": None if venue_response is None else venue_response.get("fee_ccy"),
            "fee_rate": None if venue_response is None else venue_response.get("fee_rate"),
            "fill_ids": None if venue_response is None else venue_response.get("fill_ids"),
            "fill_count": None if venue_response is None else venue_response.get("fill_count"),
            "verified_entry": None if venue_response is None else venue_response.get("verified_entry"),
            "live_contracts": None if venue_response is None else venue_response.get("live_contracts"),
            "live_side": None if venue_response is None else venue_response.get("live_side"),
            "verification_attempts": None if venue_response is None else venue_response.get("verification_attempts"),
        }
        updated_positions = list(existing_positions) + [position]
        allocate_margin = (venue_response is None or verified_entry)
        entry_fee_usdt = 0.0 if venue_response is None else float(venue_response.get("fee_usdt") or 0.0)
        state_patch = {
            "positions": {position_key: updated_positions},
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
                    "available_usdt": float(bucket.get("available_usdt") or 0.0) - (margin_required_usdt if allocate_margin else 0.0),
                    "allocated_usdt": float(bucket.get("allocated_usdt") or 0.0) + (margin_required_usdt if allocate_margin else 0.0),
                    "fees_usdt": float(bucket.get("fees_usdt") or 0.0) + entry_fee_usdt,
                    "last_leverage": leverage,
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
        positions: list[dict],
        reason: str,
        bar_id: int,
        bucket: dict,
        exit_side: str | None = None,
    ) -> ExecutionResult:
        open_positions = [p for p in positions if p.get("status") == "open"]
        if exit_side is not None:
            open_positions = [p for p in open_positions if p.get("side") == exit_side]

        total_amount = sum(float(p.get("amount") or 0.0) for p in open_positions)
        venue_response = None
        mode = "dry_run"
        submitted = False
        if self.armed and open_positions:
            if self.client is None:
                raise RuntimeError("Executor is armed but no exchange client was supplied.")
            venue_response = self.client.create_exit_order(symbol, open_positions[0].get("side", "long"), total_amount)
            mode = "demo_submit"
            submitted = True

        verified_flat = True if venue_response is None else bool(venue_response.get("verified_flat", False))
        released_usdt = 0.0 if (venue_response is not None and not verified_flat) else sum(float(p.get("margin_required_usdt") or p.get("notional_usdt") or 0.0) for p in open_positions)
        closed_ids = {id(p) for p in open_positions}
        updated_positions: list[dict] = []
        realized_pnl_total = 0.0
        for position in positions:
            if id(position) in closed_ids:
                next_status = "closed" if (venue_response is None or verified_flat) else "exit_verifying"
                next_exit_status = None if venue_response is None else venue_response.get("status")
                next_exit_reason = reason if (venue_response is None or verified_flat) else f"{reason}|exit_incomplete"
                realized_pnl_usdt = None if venue_response is None else realized_pnl_from_prices(
                    position.get("side"),
                    position.get("amount"),
                    position.get("reference_price"),
                    venue_response.get("reference_price"),
                )
                if realized_pnl_usdt is not None and (venue_response is None or verified_flat):
                    realized_pnl_total += realized_pnl_usdt
                updated_positions.append({
                    **position,
                    "trade_id": position.get("trade_id"),
                    "status": next_status,
                    "exit_bar_id": bar_id if (venue_response is None or verified_flat) else position.get("exit_bar_id"),
                    "last_confirmed_live_contracts": 0.0 if (venue_response is None or verified_flat) else venue_response.get("remaining_contracts"),
                    "last_confirmed_live_side": None if (venue_response is None or verified_flat) else venue_response.get("remaining_side"),
                    "last_exchange_observed_at": datetime.now(UTC).isoformat(),
                    "exit_reason": next_exit_reason,
                    "realized_pnl_usdt": realized_pnl_usdt if (venue_response is None or verified_flat) else position.get("realized_pnl_usdt"),
                    "exit_order_id": None if venue_response is None else venue_response.get("order_id"),
                    "exit_status": next_exit_status,
                    "exit_order_side": None if venue_response is None else venue_response.get("order_side"),
                    "exit_ccxt_symbol": None if venue_response is None else venue_response.get("ccxt_symbol"),
                    "exit_requested_amount": None if venue_response is None else venue_response.get("requested_amount"),
                    "exit_amount": None if venue_response is None else venue_response.get("amount"),
                    "exit_reference_price": None if venue_response is None else venue_response.get("reference_price"),
                    "exit_fee_usdt": None if venue_response is None else venue_response.get("fee_usdt"),
                    "exit_fee_ccy": None if venue_response is None else venue_response.get("fee_ccy"),
                    "exit_fee_rate": None if venue_response is None else venue_response.get("fee_rate"),
                    "exit_fill_ids": None if venue_response is None else venue_response.get("fill_ids"),
                    "exit_fill_count": None if venue_response is None else venue_response.get("fill_count"),
                    "exit_verified_flat": verified_flat if venue_response is not None else None,
                    "exit_remaining_contracts": None if venue_response is None else venue_response.get("remaining_contracts"),
                    "exit_remaining_side": None if venue_response is None else venue_response.get("remaining_side"),
                    "exit_order_attempts": None if venue_response is None else venue_response.get("order_attempts"),
                })
            else:
                updated_positions.append(position)

        event_realized_pnl_usdt = None if open_positions else 0.0
        if open_positions and verified_flat:
            event_realized_pnl_usdt = realized_pnl_total

        event = {
            "event_id": self._make_event_id(open_positions[0].get("trade_id", position_key), "exit", bar_id) if open_positions else self._make_event_id(position_key, "exit", bar_id),
            "trade_id": open_positions[0].get("trade_id", position_key) if open_positions else position_key,
            "type": "exit",
            "position_key": position_key,
            "symbol": symbol,
            "strategy": strategy,
            "side": exit_side,
            "reason": reason,
            "bar_id": bar_id,
            "mode": mode,
            "released_usdt": released_usdt,
            "tracked_amount": total_amount,
            "realized_pnl_usdt": event_realized_pnl_usdt,
            "venue_order_id": None if venue_response is None else venue_response.get("order_id"),
            "venue_status": None if venue_response is None else venue_response.get("status"),
            "venue_order_side": None if venue_response is None else venue_response.get("order_side"),
            "venue_ccxt_symbol": None if venue_response is None else venue_response.get("ccxt_symbol"),
            "requested_amount": None if venue_response is None else venue_response.get("requested_amount"),
            "executed_amount": None if venue_response is None else venue_response.get("amount"),
            "reference_price": None if venue_response is None else venue_response.get("reference_price"),
            "fee_usdt": None if venue_response is None else venue_response.get("fee_usdt"),
            "fee_ccy": None if venue_response is None else venue_response.get("fee_ccy"),
            "fee_rate": None if venue_response is None else venue_response.get("fee_rate"),
            "fill_ids": None if venue_response is None else venue_response.get("fill_ids"),
            "fill_count": None if venue_response is None else venue_response.get("fill_count"),
            "verified_flat": None if venue_response is None else venue_response.get("verified_flat"),
            "remaining_contracts": None if venue_response is None else venue_response.get("remaining_contracts"),
            "remaining_side": None if venue_response is None else venue_response.get("remaining_side"),
            "verification_attempts": None if venue_response is None else venue_response.get("verification_attempts"),
            "order_attempts": None if venue_response is None else venue_response.get("order_attempts"),
        }
        exit_fee_usdt = 0.0 if venue_response is None else float(venue_response.get("fee_usdt") or 0.0)
        state_patch = {
            "positions": {position_key: updated_positions},
            "last_signals": {
                position_key: {
                    "side": "flat" if exit_side is None else exit_side,
                    "reason": reason,
                    "bar_id": bar_id,
                }
            },
            "buckets": {
                position_key: {
                    **bucket,
                    "available_usdt": float(bucket.get("available_usdt") or 0.0) + released_usdt,
                    "allocated_usdt": max(0.0, float(bucket.get("allocated_usdt") or 0.0) - released_usdt),
                    "fees_usdt": float(bucket.get("fees_usdt") or 0.0) + exit_fee_usdt,
                    "realized_pnl_usdt": float(bucket.get("realized_pnl_usdt") or 0.0) + (realized_pnl_total if verified_flat else 0.0),
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

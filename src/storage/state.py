from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


DEFAULT_STATE = {
    "open_positions": 0,
    "positions": {},
    "last_signals": {},
    "history": [],
    "buckets": {},
}


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self.path.exists():
            return deepcopy(DEFAULT_STATE)
        data = json.loads(self.path.read_text())
        merged = deepcopy(DEFAULT_STATE)
        merged.update(data)
        merged["positions"] = self._migrate_positions(data.get("positions", {}))
        merged["last_signals"] = self._migrate_last_signals(data.get("last_signals", {}))
        merged["history"] = self._migrate_history(data.get("history", []))
        merged["buckets"] = self._build_buckets(data.get("buckets", {}), merged["positions"])
        merged["open_positions"] = self._count_open_positions(merged["positions"])
        return merged

    def save(self, data: dict) -> None:
        payload = deepcopy(data)
        payload["open_positions"] = self._count_open_positions(payload.get("positions", {}))
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _count_open_positions(self, positions: dict) -> int:
        total = 0
        for value in positions.values():
            if isinstance(value, list):
                total += sum(1 for item in value if item.get("status") == "open")
            elif isinstance(value, dict) and value.get("status") == "open":
                total += 1
        return total

    def _migrate_positions(self, positions: dict) -> dict:
        migrated = {}
        for key, position in positions.items():
            if isinstance(position, list):
                migrated[key] = [self._normalize_position_fields(item, key) for item in position]
                continue
            if ":" in key:
                migrated[key] = [position]
                continue
            new_key = f"breakout:{key}"
            migrated[new_key] = [self._normalize_position_fields({
                **position,
                "position_key": new_key,
                "strategy": position.get("strategy", "breakout"),
                "symbol": position.get("symbol", key),
            }, new_key)]
        return migrated

    def _normalize_position_fields(self, position: dict, key: str) -> dict:
        normalized = dict(position)
        normalized.setdefault("position_key", key)
        normalized.setdefault("trade_id", normalized.get("entry_id") or key)
        normalized.setdefault("venue_order_side", None)
        normalized.setdefault("venue_ccxt_symbol", normalized.get("symbol"))
        normalized.setdefault("requested_notional_usdt", normalized.get("notional_usdt"))
        normalized.setdefault("requested_amount", normalized.get("amount"))
        normalized.setdefault("fee_usdt", None)
        normalized.setdefault("last_confirmed_live_contracts", None)
        normalized.setdefault("last_confirmed_live_side", None)
        normalized.setdefault("last_exchange_observed_at", None)
        normalized.setdefault("reconcile_reason", None)
        normalized.setdefault("exit_order_side", None)
        normalized.setdefault("exit_ccxt_symbol", normalized.get("symbol"))
        normalized.setdefault("exit_requested_amount", normalized.get("exit_amount", normalized.get("amount")))
        normalized.setdefault("exit_amount", None)
        normalized.setdefault("exit_reference_price", None)
        normalized.setdefault("exit_fee_usdt", None)
        return normalized

    def _migrate_last_signals(self, last_signals: dict) -> dict:
        migrated = {}
        for key, signal in last_signals.items():
            new_key = key if ":" in key else f"breakout:{key}"
            migrated[new_key] = signal
        return migrated

    def _migrate_history(self, history: list[dict]) -> list[dict]:
        migrated = []
        for event in history:
            if "position_key" in event:
                event = dict(event)
                event.setdefault("trade_id", event.get("position_key"))
                event.setdefault("event_id", f"{event.get('trade_id')}:{event.get('type', 'event')}:{event.get('bar_id', 'na')}")
                migrated.append(event)
                continue
            symbol = event.get("symbol")
            strategy = event.get("strategy", "breakout")
            migrated.append({
                **event,
                "strategy": strategy,
                "position_key": f"{strategy}:{symbol}" if symbol else None,
            })
        return migrated

    def _build_buckets(self, buckets: dict, positions: dict) -> dict:
        normalized = deepcopy(buckets)
        for key, bucket in list(normalized.items()):
            if ":" not in key:
                normalized[f"breakout:{key}"] = {
                    **bucket,
                    "strategy": bucket.get("strategy", "breakout"),
                    "symbol": bucket.get("symbol", key),
                    "locked": bucket.get("locked", False),
                    "lock_reason": bucket.get("lock_reason"),
                }
                normalized.pop(key)

        for key, position_list in positions.items():
            positions_for_key = position_list if isinstance(position_list, list) else [position_list]
            if key not in normalized:
                initial_capital = max(500.0, sum(float(p.get("notional_usdt") or 0.0) for p in positions_for_key) or 500.0)
                allocated = sum(float(p.get("notional_usdt") or 0.0) for p in positions_for_key if p.get("status") == "open")
                sample = positions_for_key[0] if positions_for_key else {}
                normalized[key] = {
                    "strategy": sample.get("strategy", key.split(":", 1)[0]),
                    "symbol": sample.get("symbol", key.split(":", 1)[-1]),
                    "initial_capital_usdt": initial_capital,
                    "available_usdt": max(0.0, initial_capital - allocated),
                    "allocated_usdt": allocated,
                    "locked": False,
                    "lock_reason": None,
                }
        for key, bucket in normalized.items():
            bucket.setdefault("locked", False)
            bucket.setdefault("lock_reason", None)
        return normalized

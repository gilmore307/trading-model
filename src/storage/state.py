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
        merged["open_positions"] = sum(
            1 for item in merged["positions"].values() if item.get("status") == "open"
        )
        return merged

    def save(self, data: dict) -> None:
        payload = deepcopy(data)
        payload["open_positions"] = sum(
            1 for item in payload.get("positions", {}).values() if item.get("status") == "open"
        )
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _migrate_positions(self, positions: dict) -> dict:
        migrated = {}
        for key, position in positions.items():
            if ":" in key:
                migrated[key] = position
                continue
            new_key = f"breakout:{key}"
            migrated[new_key] = {
                **position,
                "position_key": new_key,
                "strategy": position.get("strategy", "breakout"),
                "symbol": position.get("symbol", key),
            }
        return migrated

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
                }
                normalized.pop(key)

        for key, position in positions.items():
            if key not in normalized:
                initial_capital = float(position.get("notional_usdt") or 500.0)
                allocated = float(position.get("notional_usdt") or 0.0) if position.get("status") == "open" else 0.0
                normalized[key] = {
                    "strategy": position.get("strategy", key.split(":", 1)[0]),
                    "symbol": position.get("symbol", key.split(":", 1)[-1]),
                    "initial_capital_usdt": max(500.0, initial_capital),
                    "available_usdt": max(0.0, max(500.0, initial_capital) - allocated),
                    "allocated_usdt": allocated,
                }
        return normalized

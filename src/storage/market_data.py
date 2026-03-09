from __future__ import annotations

import json
from pathlib import Path


class MarketDataStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_dir = self.root / "events"
        self.ohlc_dir = self.root / "ohlc" / "1m"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.ohlc_dir.mkdir(parents=True, exist_ok=True)

    def append_ohlc(self, execution_symbol: str, candles: list[list[float]]) -> int:
        symbol_key = execution_symbol.replace("/", "_").replace(":", "_")
        path = self.ohlc_dir / f"{symbol_key}.jsonl"
        existing = set()
        if path.exists():
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        existing.add(int(row["ts"]))
                    except Exception:
                        continue
        written = 0
        with path.open("a") as f:
            for candle in candles:
                ts = int(candle[0])
                if ts in existing:
                    continue
                row = {
                    "ts": ts,
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                }
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
                written += 1
        return written

    def append_events(self, events: list[dict]) -> int:
        if not events:
            return 0
        path = self.events_dir / "trades.jsonl"
        with path.open("a") as f:
            for event in events:
                f.write(json.dumps(event, separators=(",", ":"), default=str) + "\n")
        return len(events)

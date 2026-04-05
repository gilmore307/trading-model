from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_model.io.jsonl import read_jsonl


BAR_COLUMNS = [
    "ts",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "vwap",
]


def load_bars(data_root: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month in months:
        path = data_root / symbol / month / "bars_1min.jsonl"
        if not path.exists():
            continue
        frame = read_jsonl(path)
        if frame.empty:
            continue
        available = [col for col in BAR_COLUMNS if col in frame.columns]
        frame = frame[available].copy()
        frame["symbol"] = symbol
        frame["month"] = month
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No bar data found for {symbol=} {months=}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged

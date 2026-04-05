from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trading_model.io.jsonl import read_jsonl


def _safe_load_meta(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_variant_returns(strategy_root: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    symbol_root = strategy_root / symbol
    frames: list[pd.DataFrame] = []
    if not symbol_root.exists():
        raise FileNotFoundError(f"Missing strategy root for {symbol}: {symbol_root}")

    for family_dir in sorted(p for p in symbol_root.iterdir() if p.is_dir()):
        if family_dir.name == "global_oracle":
            continue
        for variant_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            for month in months:
                returns_path = variant_dir / month / "returns.jsonl"
                meta_path = variant_dir / month / "meta.json"
                if not returns_path.exists() or not meta_path.exists():
                    continue
                frame = read_jsonl(returns_path)
                if frame.empty:
                    continue
                meta = _safe_load_meta(meta_path)
                frame["symbol"] = symbol
                frame["family_id"] = meta.get("family_id", family_dir.name)
                frame["variant_id"] = meta.get("variant_id", variant_dir.name)
                frame["strategy_partition_month"] = meta.get("month_key", month)
                frame["strategy_run_id"] = f"{symbol}:{frame['family_id'].iloc[0]}:{frame['variant_id'].iloc[0]}:{month}"
                frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No variant returns found for {symbol=} {months=}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["family_id", "variant_id", "ts"]).reset_index(drop=True)
    return merged


def load_global_oracle_returns(strategy_root: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    oracle_root = strategy_root / symbol / "global_oracle" / "global_oracle"
    frames: list[pd.DataFrame] = []
    for month in months:
        returns_path = oracle_root / month / "returns.jsonl"
        meta_path = oracle_root / month / "meta.json"
        if not returns_path.exists() or not meta_path.exists():
            continue
        frame = read_jsonl(returns_path)
        if frame.empty:
            continue
        meta = _safe_load_meta(meta_path)
        frame["symbol"] = symbol
        frame["global_oracle_selected_variant_id"] = frame.get("selected_variant_id")
        frame["global_oracle_selected_family_id"] = frame.get("selected_family_id")
        frame["oracle_partition_month"] = meta.get("month_key", month)
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No global oracle returns found for {symbol=} {months=}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged

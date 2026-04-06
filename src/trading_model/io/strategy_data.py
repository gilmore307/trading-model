from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trading_model.io.jsonl import read_jsonl


def _safe_load_meta(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_variant_month(variant_dir: Path, family_dir: Path, symbol: str, month: str) -> pd.DataFrame | None:
    equity_path = variant_dir / month / "equity.jsonl"
    returns_path = variant_dir / month / "returns.jsonl"
    meta_path = variant_dir / month / "meta.json"
    if not equity_path.exists() or not meta_path.exists():
        return None

    equity = read_jsonl(equity_path)
    if equity.empty:
        return None
    returns = read_jsonl(returns_path) if returns_path.exists() else pd.DataFrame(columns=["ts", "bar_return"])
    meta = _safe_load_meta(meta_path)

    merged = equity.merge(
        returns[[col for col in returns.columns if col in {"ts", "bar_return", "selected_variant_id", "selected_family_id"}]],
        on="ts",
        how="left",
        suffixes=("", "_returns"),
    )
    if "bar_return_returns" in merged.columns:
        merged["bar_return"] = merged["bar_return"].fillna(merged["bar_return_returns"])
        merged = merged.drop(columns=["bar_return_returns"])

    merged["symbol"] = symbol
    merged["family_id"] = meta.get("family_id", family_dir.name)
    merged["variant_id"] = meta.get("variant_id", variant_dir.name)
    merged["strategy_partition_month"] = meta.get("month_key", month)
    merged["strategy_run_id"] = f"{symbol}:{merged['family_id'].iloc[0]}:{merged['variant_id'].iloc[0]}:{month}"
    return merged


def load_variant_returns(
    strategy_root: Path,
    symbol: str,
    months: list[str],
    *,
    variant_limit: int | None = None,
) -> pd.DataFrame:
    symbol_root = strategy_root / symbol
    frames: list[pd.DataFrame] = []
    loaded_variants = 0
    if not symbol_root.exists():
        raise FileNotFoundError(f"Missing strategy root for {symbol}: {symbol_root}")

    for family_dir in sorted(p for p in symbol_root.iterdir() if p.is_dir()):
        if family_dir.name == "global_oracle":
            continue
        for variant_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            if variant_limit is not None and loaded_variants >= variant_limit:
                break
            variant_frames: list[pd.DataFrame] = []
            for month in months:
                frame = _load_variant_month(variant_dir, family_dir, symbol, month)
                if frame is not None:
                    variant_frames.append(frame)
            if variant_frames:
                frames.append(pd.concat(variant_frames, ignore_index=True))
                loaded_variants += 1
        if variant_limit is not None and loaded_variants >= variant_limit:
            break

    if not frames:
        raise FileNotFoundError(f"No variant returns found for {symbol=} {months=}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["family_id", "variant_id", "ts"]).reset_index(drop=True)
    return merged


def load_global_oracle_returns(strategy_root: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    oracle_root = strategy_root / symbol / "global_oracle" / "global_oracle"
    frames: list[pd.DataFrame] = []
    for month in months:
        equity_path = oracle_root / month / "equity.jsonl"
        returns_path = oracle_root / month / "returns.jsonl"
        meta_path = oracle_root / month / "meta.json"
        if not equity_path.exists() or not meta_path.exists():
            continue
        equity = read_jsonl(equity_path)
        if equity.empty:
            continue
        returns = read_jsonl(returns_path) if returns_path.exists() else pd.DataFrame(columns=["ts", "bar_return"])
        meta = _safe_load_meta(meta_path)
        merged = equity.merge(
            returns[[col for col in returns.columns if col in {"ts", "bar_return", "selected_variant_id", "selected_family_id"}]],
            on="ts",
            how="left",
            suffixes=("", "_returns"),
        )
        if "bar_return_returns" in merged.columns:
            merged["bar_return"] = merged["bar_return"].fillna(merged["bar_return_returns"])
            merged = merged.drop(columns=["bar_return_returns"])
        merged["symbol"] = symbol
        merged["global_oracle_selected_variant_id"] = merged.get("selected_variant_id")
        merged["global_oracle_selected_family_id"] = merged.get("selected_family_id")
        merged["oracle_partition_month"] = meta.get("month_key", month)
        frames.append(merged)
    if not frames:
        raise FileNotFoundError(f"No global oracle returns found for {symbol=} {months=}")
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged

from __future__ import annotations

from pathlib import Path

import pandas as pd


def scan_symbol_month_availability(trading_data_root: Path, trading_strategy_root: Path, symbols: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for symbol in symbols:
        data_symbol_root = trading_data_root / symbol
        strategy_symbol_root = trading_strategy_root / symbol
        data_months = set()
        strategy_months = set()
        if data_symbol_root.exists():
            for month_dir in sorted(p for p in data_symbol_root.iterdir() if p.is_dir()):
                if (month_dir / "bars_1min.jsonl").exists():
                    data_months.add(month_dir.name)
        if strategy_symbol_root.exists():
            for family_dir in sorted(p for p in strategy_symbol_root.iterdir() if p.is_dir() and p.name != "global_oracle"):
                for variant_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
                    for month_dir in sorted(p for p in variant_dir.iterdir() if p.is_dir()):
                        if (month_dir / "equity.jsonl").exists() and (month_dir / "returns.jsonl").exists():
                            strategy_months.add(month_dir.name)
            oracle_root = strategy_symbol_root / "global_oracle" / "global_oracle"
            oracle_months = {p.name for p in oracle_root.iterdir() if p.is_dir()} if oracle_root.exists() else set()
        else:
            oracle_months = set()
        shared_months = sorted(data_months & strategy_months & oracle_months)
        rows.append(
            {
                "symbol": symbol,
                "data_months": sorted(data_months),
                "strategy_months": sorted(strategy_months),
                "oracle_months": sorted(oracle_months),
                "shared_months": shared_months,
                "shared_month_count": len(shared_months),
            }
        )
    return pd.DataFrame(rows)

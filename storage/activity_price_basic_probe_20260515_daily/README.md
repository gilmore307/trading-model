# Activity-price basic daily probe — 2026-05-15

Exploratory, not production-calibrated. Tests abnormal activity vs subsequent stock price paths using daily Alpaca bars only.

Universe: AAPL, MSFT, NVDA, AMD, JPM, COIN, XOM, CVX, LLY, PFE, RKLB, ACHR, ASTS, RCAT, CAVA, ELF, VKTX, SAVA. Benchmark: SPY.
Window: 2024-01-01 through 2025-05-01. Detector: trading-data equity abnormal activity detector with exploratory z>=2 / gap>=4% thresholds.

Outputs:
- `labeled_daily_windows.csv` — per-symbol daily windows with abnormal flag and forward labels.
- `per_symbol_summary.csv` — bars/eligible/abnormal counts by symbol.
- `group_stats.csv` — abnormal/non-abnormal/activity-token comparisons.
- `report.json` — run metadata and headline group stats.

2026-05-15 correction: Directional average forward return is not the primary proof metric because downside paths are tradable too. Added:
- `absolute_move_group_stats.csv` — absolute forward returns and 5d tradeable-excursion proxy by group/activity token/bucket.
- `absolute_move_per_symbol_delta.csv` — abnormal minus non-abnormal absolute-move deltas by symbol.

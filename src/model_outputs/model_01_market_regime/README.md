# model_01_market_regime

Continuous MarketRegimeModel V1 state-vector builder.

Boundary:

- Input: rows from `trading_data.feature_01_market_regime`.
- Output: rows for `trading_model.model_01_market_regime` plus per-ETF affinity rows for `trading_model.model_01_market_regime_etf_affinity`.
- Row key: `available_time`.
- No clustering, hard state labels, supervised regime labels, provider calls, or durable writes in the pure generator.

Runtime SQL reads/writes are isolated in `scripts/generate_model_01_market_regime.py`.

## Config

`config/factor_specs.toml` owns factor membership, signal directions, reducer choices, and standardization defaults.

Supported group forms:

- explicit columns: `columns = ["hyg_lqd_30m", ...]`
- symbol/suffix expansion: `symbols = ["spy", "qqq"]` plus `suffixes = ["return_20d"]`

Supported reducers:

- `bounded_mean` → `tanh(mean(zscores) / 2)`
- `bounded_abs_mean` → `tanh(mean(abs(zscores)) / 2)`

Supported aggregations:

- `flat` → reduce all eligible signals directly
- `bucketed_mean` → average eligible signals by symbol bucket first, then reduce bucket scores

Standardization defaults are currently `lookback = 120`, `min_history = 20`, `std_floor = 1e-8`, `z_clip = 5.0`, and `min_signal_coverage = 0.5`. Groups may override `min_history`, `std_floor`, or `z_clip`; correlation/volatility/low-frequency groups deliberately use longer minimum histories.


## ETF affinity output

`generate_etf_affinity_rows()` adds the practical Layer 1 bridge from market state to ETF/security selection. For each `available_time + etf_symbol`, it emits:

- `etf_trend_score` — point-in-time ETF trend/technical leadership from rolling z-scores;
- `etf_relative_strength_score` — ETF relative strength versus SPY when available;
- `market_state_tailwind_score` — heuristic alignment between the current market-state vector and ETF role;
- `market_state_affinity_score` — combined ETF suitability score for the current tape;
- `confidence_score` — signal coverage plus state-vector data quality.

This output is still Layer 1. It says which ETFs historically/currently fit the detected tape and gives `SecuritySelectionModel` sector/style/theme direction. It does not choose final stock candidates, final weights, or risk-gated positions. Future returns remain evaluation labels, not inputs to the production affinity score.

# model_01_market_regime

Continuous MarketRegimeModel V1 state-vector builder.

Boundary:

- Input: rows from `trading_data.feature_01_market_regime`.
- Output: rows for `trading_model.model_01_market_regime`.
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


## Factor ontology direction

The current implementation is a first proxy-backed slice. Its observable inputs include ETF ratios, returns, volatility, trend, correlation, and breadth signals. The durable Model 1 direction is deeper: output factors should describe market properties such as price behavior, trend certainty, capital/funding flow, sentiment, valuation pressure, fundamentals, macro environment, market-wide structure, and risk stress.

Proxy signals are sensors; they are not the conceptual factor ontology. A later reviewed migration should update concrete output columns/config/tests only after the deeper factor definitions are settled.


## Evidence coverage gap

The current Layer 1 feature payload has 967 logical feature keys after moving sector/industry rotation pairs to `feature_02_security_selection`, while the first factor specification uses 125 signal columns. That provisional ~12.9% utilization is intentionally not the final target. Future factor work should expand coverage through a reviewed feature-to-latent-factor evidence map rather than by blindly ingesting every generated column.


## Sector rotation boundary

Sector/industry rotation, sector leadership, and sector-vs-sector relative strength belong to `SecuritySelectionModel`. Model 1 may use market-wide breadth, concentration, crowding, correlation, and fragility evidence, but it should not output a sector rotation factor or candidate-facing sector leadership conclusion.


## Cross-asset proxy boundary

Long/short bond ratios such as `TLT/SHY` and `IEF/SHY` may remain Model 1 evidence because they describe broad discount-rate, duration, and term-structure pressure. They are sensors, not final factor names and not candidate choices. Sector/industry ETF comparisons are different: those answer rotation/leadership questions and belong to `SecuritySelectionModel`.

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


## Market-property factor ontology

The current output columns are market-property factors, not proxy-dashboard factors:

- `price_behavior_factor`
- `trend_certainty_factor`
- `capital_flow_factor`
- `sentiment_factor`
- `valuation_pressure_factor`
- `fundamental_strength_factor`
- `macro_environment_factor`
- `market_structure_factor`
- `risk_stress_factor`
- `transition_pressure`
- `data_quality_score`

Observable ETF ratios, returns, volatility, trend, correlation, credit/rate/dollar/commodity, and breadth signals are sensors. They support the market-property ontology but are not themselves the public output contract. `fundamental_strength_factor` is currently a broad-market participation proxy until true point-in-time fundamental evidence is added.


## Evidence coverage gap

The current Layer 1 feature payload has 857 logical feature keys after moving sector/industry rotation pairs and sector-observation aggregates to `feature_02_security_selection` and pruning raw ratio moving-average levels and standalone SHY return/trend keys, while the expanded factor specification owns all 857 signal columns. This is an ownership baseline, not a claim that the factor ontology is final: future feature additions must either map to a reviewed factor/diagnostic role or be removed rather than silently expanding the payload.


## Sector rotation boundary

Sector/industry rotation, sector leadership, and sector-vs-sector relative strength belong to `SecuritySelectionModel`. Model 1 may use market-wide breadth, concentration, crowding, correlation, and fragility evidence, but it should not output a sector rotation factor or candidate-facing sector leadership conclusion.


## Cross-asset proxy boundary

Long/short bond ratios such as `TLT/SHY` and `IEF/SHY` may remain Model 1 evidence because they describe broad discount-rate, duration, and term-structure pressure. They are sensors, not final factor names and not candidate choices. Sector/industry ETF comparisons are different: those answer rotation/leadership questions and belong to `SecuritySelectionModel`.

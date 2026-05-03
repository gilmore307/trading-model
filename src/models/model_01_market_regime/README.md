# model_01_market_regime

Continuous MarketRegimeModel V1 state-vector builder.

Boundary:

- Input: rows from `trading_data.feature_01_market_regime`.
- Primary output: rows for `trading_model.model_01_market_regime`.
- Optional support outputs: rows for `trading_model.model_01_market_regime_explainability` and `trading_model.model_01_market_regime_diagnostics`.
- Row key: `available_time`; explainability is keyed by `(available_time, factor_name)`.
- No clustering, hard state labels, supervised regime labels, provider calls, or durable writes in the pure generator.

Runtime SQL reads/writes are isolated in `scripts/generate_model_01_market_regime.py`.

## Config

`config/factor_specs.toml` owns factor membership, signal directions, reducer choices, and standardization defaults.

`evidence_map.md` owns the reviewed evidence-role contract for current Layer 1 signals and downstream usefulness checks.

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

- `1_price_behavior_factor`
- `1_trend_certainty_factor`
- `1_capital_flow_factor`
- `1_sentiment_factor`
- `1_valuation_pressure_factor`
- `1_fundamental_strength_factor`
- `1_macro_environment_factor`
- `1_market_structure_factor`
- `1_risk_stress_factor`
- `1_transition_pressure`
- `1_data_quality_score`

When writing to SQL, the runtime wrapper preserves compact model-facing keys such as `1_trend_certainty_factor` as the physical column name and quotes numeric-leading identifiers where required. The support artifact builders are intentionally generic: explainability stores reviewed per-factor context, while diagnostics stores row-level coverage/missingness/gating context. If a future model layer genuinely has no support artifact to write, the Layer naming contract does not require inventing one.

Observable ETF ratios, returns, volatility, trend, correlation, credit/rate/dollar/commodity, and breadth signals are sensors. They support the market-property ontology but are not themselves the public output contract. `1_fundamental_strength_factor` is currently a broad-market participation proxy until true point-in-time fundamental evidence is added.


## Evidence map

The current Layer 1 feature payload has 857 logical feature keys after moving sector/industry rotation pairs and sector-observation aggregates to `feature_02_sector_context` and pruning raw ratio moving-average levels and standalone SHY return/trend keys, while the expanded factor specification owns all 857 signal columns. This is an ownership baseline, not a claim that the factor ontology is final.

See `evidence_map.md` for the current feature-to-factor evidence map, evidence-role vocabulary, intentionally unused evidence, quality evidence, and market-context usefulness checks. Future feature additions must either map to a reviewed primary/diagnostic/quality/evaluation role or be removed rather than silently expanding the payload.


## Sector rotation boundary

Sector/industry rotation, sector leadership, and sector-vs-sector relative strength belong to `SectorContextModel`. Model 1 may use market-wide breadth, concentration, crowding, correlation, and fragility evidence, but it should not output a sector rotation factor or candidate-facing sector leadership conclusion.


## Cross-asset proxy boundary

Long/short bond ratios such as `TLT/SHY` and `IEF/SHY` may remain Model 1 evidence because they describe broad discount-rate, duration, and term-structure pressure. They are sensors, not final factor names and not candidate choices. Sector/industry ETF comparisons are different: those answer rotation/leadership questions and belong to `SectorContextModel`.

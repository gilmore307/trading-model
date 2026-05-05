# model_01_market_regime

MarketRegimeModel V2.2 broad market-context state builder.

Boundary:

- Input: rows from `trading_data.feature_01_market_regime`.
- Primary output: rows for `trading_model.model_01_market_regime`.
- Support outputs: rows for `trading_model.model_01_market_regime_explainability` and `trading_model.model_01_market_regime_diagnostics`.
- Row key: `available_time`; explainability is keyed by `(available_time, factor_name)`.
- No clustering, hard state labels, supervised regime labels, provider calls, or durable writes in the pure generator.

Runtime SQL reads/writes are isolated in `scripts/generate_model_01_market_regime.py`.

## Output contract

Layer 1 describes broad market tradability/regime context with separate direction, trend quality, stability, risk/stress, transition risk, breadth, correlation/crowding, dispersion, liquidity pressure/support, coverage, and data-quality semantics. It does not output alpha confidence, target state vectors, selected sectors, selected securities, option contracts, position sizes, or trading instructions.

Current primary output columns:

- `available_time`
- `1_market_direction_score`
- `1_market_direction_strength_score`
- `1_market_trend_quality_score`
- `1_market_stability_score`
- `1_market_risk_stress_score`
- `1_market_transition_risk_score`
- `1_breadth_participation_score`
- `1_correlation_crowding_score`
- `1_dispersion_opportunity_score`
- `1_market_liquidity_pressure_score`
- `1_market_liquidity_support_score`
- `1_coverage_score`
- `1_data_quality_score`

When writing to SQL, the runtime wrapper preserves compact model-facing keys such as `1_market_trend_quality_score` as physical column names and quotes numeric-leading identifiers where required. Explainability stores reviewed semantic-output context; diagnostics stores row-level coverage, missingness, and gating context.

## Config and internal signal groups

`config/factor_specs.toml` owns internal signal-group membership, signal directions, reducer choices, and standardization defaults. These groups are implementation evidence reducers, not the public downstream output contract.

`evidence_map.md` owns the reviewed evidence-role contract for Layer 1 signals and downstream usefulness checks.

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

## Evidence map

The current Layer 1 feature payload has 857 logical feature keys after moving sector/industry rotation pairs and sector-observation aggregates to `feature_02_sector_context` and pruning raw ratio moving-average levels and standalone SHY return/trend keys, while the internal signal specification owns all 857 signal columns. This is an ownership baseline, not a claim that every reducer is promotion-ready.

See `evidence_map.md` for the current feature-to-output evidence map, evidence-role vocabulary, intentionally unused evidence, quality evidence, and market-context usefulness checks. Future feature additions must either map to a reviewed primary/diagnostic/quality/evaluation role or be removed rather than silently expanding the payload.

## Sector rotation boundary

Sector/industry rotation, sector leadership, and sector-vs-sector relative strength belong to `SectorContextModel`. Model 1 may use market-wide breadth, concentration, crowding, correlation, and fragility evidence, but it must not output a sector rotation factor or candidate-facing sector leadership conclusion.

## Cross-asset proxy boundary

Long/short bond ratios such as `TLT/SHY` and `IEF/SHY` may remain Model 1 evidence because they describe broad discount-rate, duration, and term-structure pressure. They are sensors, not final factor names and not candidate choices. Sector/industry ETF comparisons are different: those answer rotation/leadership questions and belong to `SectorContextModel`.

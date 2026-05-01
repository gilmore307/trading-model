# Model Decomposition Framework

Status: draft  
Owner intent: use one reviewable structure for every model layer before implementation, evaluation, or promotion work expands.

## Purpose

Every `trading-model` layer must be explained with the same nine-part decomposition before its implementation is treated as accepted design:

1. **Data** — what point-in-time input tables/artifacts are eligible, who owns them, and which timestamps define availability.
2. **Features** — what model-facing `X` fields are built from the data and which fields are diagnostic, evaluation-only, or intentionally unused.
3. **Prediction target** — what `y` is predicted, scored, ranked, optimized, or inferred; if unsupervised, what latent state/vector replaces a supervised target.
4. **Model mapping** — how the model maps `X` to `y` or to the output vector/parameter surface.
5. **Loss / error measure** — how wrongness is measured during fitting, scoring, calibration, or evaluation.
6. **Training / parameter update** — how parameters, thresholds, scalers, weights, or rules are updated over time without leakage.
7. **Validation / usefulness** — how the layer proves it helps the trading decision stack rather than merely fitting history.
8. **Overfitting control** — how the layer avoids hindsight, data snooping, unstable refits, over-complexity, and false confidence.
9. **Decision deployment** — how the output enters the real decision flow, including downstream consumers, gates, audit rows, and non-owned live execution boundaries.

This is a design and review template, not a mandate that every layer must be a supervised predictive model. Some layers produce continuous state vectors, parameter surfaces, rankers, overlays, or risk gates.

## Cross-Layer Rules

- Preserve point-in-time semantics: every row must be keyed by a time that was genuinely knowable to the system.
- Keep data acquisition and source evidence in `trading-data`; keep global shared contracts and registry terms routed through `trading-manager`.
- Do not collapse rich context into a scalar unless the retained output also preserves enough supporting fields for audit and downstream interpretation.
- Validation must test decision usefulness and leakage resistance, not only statistical fit.
- Deployment means offline decision-record integration in this repository; live/paper order mutation remains outside `trading-model`.

## Layer 1 Decomposition: MarketRegimeModel

Status: accepted as the Layer 1 V1 contract on 2026-05-01.

### 1. Data

Primary input:

```text
trading_data.feature_01_market_regime
```

Eligible evidence is broad-market, cross-asset, credit/rate/dollar/commodity, volatility, breadth, correlation, concentration, trend, and market-structure evidence available at or before `available_time`.

Layer 1 must not use sector/industry rotation labels, selected securities, strategy performance, option-contract outcomes, portfolio PnL, or future-return labels as construction inputs.

### 2. Features

`X` is the point-in-time feature vector from `feature_01_market_regime`, grouped into reviewed evidence blocks such as:

- price behavior and broad index returns;
- trend certainty and momentum persistence;
- volatility, correlation, breadth, and market-structure stress;
- credit, rate, dollar, commodity, and funding/liquidity proxies;
- sentiment/risk-appetite proxies;
- data-quality and signal-coverage diagnostics.

Feature roles must be explicit:

- **used** — contributes to a factor;
- **diagnostic/quality** — informs confidence or data quality;
- **evaluation-only** — used only after output construction to test usefulness;
- **intentionally unused** — excluded with a reason.

### 3. Prediction target

V1 has no supervised target and no required hard regime label.

The output is a continuous point-in-time market-state vector for:

```text
trading_model.model_01_market_regime
```

Current output fields are market-property factors: price behavior, trend certainty, capital/funding flow, sentiment, valuation pressure, fundamental strength, macro environment, market-wide structure, risk stress, transition pressure, and data quality. Observable returns, ratios, volatility, correlation, credit/rate/dollar/commodity, breadth, and risk-appetite signals are sensors that support those properties rather than public output names.

Future-return labels may be attached later for evaluation only, not for constructing the vector.

### 4. Model mapping from X to output

Current V1 mapping:

```text
rolling/expanding point-in-time scaler
  -> per-signal z-score with clipping/floors
  -> reviewed sign direction
  -> factor-level reducer
  -> bounded continuous factor values
  -> transition pressure and data-quality score
```

No current or future row may be used to fit the scaler for the row being scored.

### 5. Loss / error measure

Because V1 is unsupervised, construction does not optimize a supervised prediction loss. Wrongness is reviewed through proxy and evaluation measures:

- leakage or timestamp violation count;
- missing/low signal coverage;
- factor instability under rolling/expanding refits;
- unintuitive sign behavior against reviewed evidence blocks;
- poor downstream separation for future risk/return/drawdown diagnostics;
- poor usefulness for option-expression constraints, strategy compatibility, or portfolio risk policy.

If later supervised/calibrated sub-models are introduced, their loss functions must be recorded separately and must not redefine the Layer 1 output as a future-return predictor.

### 6. Training / parameter update

Current parameters are reviewed configuration and rolling state, not learned black-box weights:

- factor membership and signs live in config;
- lookback, minimum history, floors, z-score clipping, reducers, and coverage thresholds are explicit;
- rolling/expanding statistics update only from prior available rows;
- config changes require tests and decision/acceptance evidence.

Future learned weights may be added only after a leakage-safe training/evaluation design is accepted.

### 7. Validation / usefulness

Validation should show that the state vector is:

- point-in-time correct;
- stable enough for decision use but responsive to actual regime transitions;
- interpretable from supporting evidence;
- useful as background context for `OptionExpressionModel`, `StrategySelectionModel`, and `PortfolioRiskModel`;
- useful for risk/drawdown/volatility-transition diagnostics;
- not acting as a hidden sector/security selector.

Minimum validation evidence should include chronological splits, factor distribution checks, stability/refit checks, evaluation labels kept outside construction, and downstream usefulness tests.

### 8. Overfitting control

Controls:

- chronological train/validation/test or walk-forward evaluation;
- no future labels in vector construction;
- limited factor count with reviewed evidence membership;
- bounded/clipped factor values;
- minimum signal coverage and data-quality scoring;
- config-driven formulas rather than ad hoc notebook tuning;
- sector/industry rotation kept out of Layer 1;
- promotion gate requires evaluation-backed evidence, not visual plausibility.

### 9. Decision deployment

Layer 1 output enters the decision stack as broad market background:

```text
model_01_market_regime
  -> strategy compatibility / disabled-strategy context
  -> option-expression constraints such as DTE, delta/moneyness, IV/theta tolerance, and no-trade filters
  -> portfolio risk/exposure/sizing/execution-policy gate
  -> unified decision record audit context
```

It must not directly rank sectors, ETFs, or stocks. `SecuritySelectionModel` owns sector/industry rotation and candidate parameter surfaces.

## Layer 2 Decomposition: SecuritySelectionModel

Status: draft for review.

### 1. Data

Status: accepted for Feature 2 rotation evidence scope on 2026-05-01.

Primary model-facing inputs:

```text
trading_data.feature_02_security_selection
etf_holding_snapshot
stock_etf_exposure          # derived point-in-time exposure surface, exact owner still open
model_01_market_regime      # background/audit/coarse gating only, not direct ranking input
```

`feature_02_security_selection` should be the Layer 2 home for the evidence moved out of `feature_01_market_regime` when Layer 1 was narrowed to broad market properties. Its V1 scope is:

- candidate-comparison rows for reviewed relative-strength combinations with `combination_type in {sector_rotation, daily_context}`;
- one per-snapshot `sector_rotation_summary` row for sector-observation breadth and dispersion aggregates;
- row key: `snapshot_time + candidate_symbol + comparison_symbol + rotation_pair_id`;
- payload: relative-strength returns, normalized trend distance/slope/spread/alignment, volatility-ratio, correlation, and sector-observation participation/dispersion evidence.

Eligible evidence:

- sector/industry ETF relative strength, trend, persistence, volatility stability, breadth, dispersion, and signal agreement from the migrated Feature 1 rotation surface;
- point-in-time sector/industry ETF holdings snapshots;
- stock-to-sector/industry ETF exposure derived from holdings weights;
- stock and ETF bars, liquidity, spread, volume, gap, volatility, and relative-strength evidence;
- optionability summaries such as option availability, spread, volume, open interest, and DTE coverage;
- event exclusions such as earnings windows, macro shock windows, SEC/news risk, abnormal activity, and known no-trade states;
- Layer 1 market-property vector only as background, audit context, or coarse no-trade/risk filter.

Excluded from construction:

- future returns as ranking inputs;
- strategy performance;
- option-contract outcomes;
- portfolio PnL;
- broad/macro ETF candidates that do not provide a sector/industry holdings bridge.

### 2. Features

`X` is a point-in-time candidate evidence surface keyed by `available_time + candidate_symbol`.

Core feature blocks:

- `sector_rotation_state_vector` — sector/industry ETF leadership, persistence, breadth support, volatility stability, and agreement;
- `stock_sector_exposure_vector` — stock exposure to eligible sector/industry ETFs from point-in-time holdings;
- `candidate_rotation_context` — sector/industry rotation evidence transmitted to an ETF or stock candidate;
- `candidate_trend_state_vector` — trend clarity, trend persistence, relative strength, choppiness, gap behavior, and volatility fit;
- `tradability_and_risk_vector` — liquidity, spread, optionability, borrow/shortability if relevant, event risk, and abnormal activity;
- `candidate_quality_diagnostics` — missing coverage, stale holdings, low liquidity, conflicting signals, or ambiguous rotation.

Candidate sources must include both:

1. sector/industry ETF holdings-driven candidates;
2. full-market scan-driven candidates.

Do not rely only on ETF holdings, because emerging stocks may appear before they become large ETF constituents.

### 3. Prediction target

V1 does not target “highest future return.”

The target is a candidate parameter surface describing which sector/industry ETFs and stocks have the clearest, most persistent, highest-certainty tradable setup.

Primary output concept:

```text
candidate_parameter_surface[available_time, candidate_symbol]
```

Possible fields:

```text
candidate_symbol
candidate_type                  # industry_etf, sector_etf, stock
candidate_rotation_context
trend_clarity_score
trend_persistence_score
relative_strength_consistency_score
signal_agreement_score
liquidity_score
optionability_score
event_risk_score
certainty_score
eligibility_state               # eligible, watch, gated, excluded
candidate_selection_parameter   # optional convenience scalar, not sole output
candidate_reason
```

Forward returns, realized drawdown, and future trade outcomes are labels for evaluation/calibration only.

### 4. Model mapping from X to output

Conceptual mapping:

```text
sector_rotation_model(feature_02_security_selection)
  -> sector_rotation_state_vector[sector_or_industry_etf]

point_in_time_holding_exposure(etf_holding_snapshot)
  -> stock_sector_exposure_vector[stock]

candidate_context_builder(
  sector_rotation_state_vector,
  stock_sector_exposure_vector,
  full_market_scan_context
)
  -> candidate_rotation_context

parameter_adjuster(
  candidate_rotation_context,
  candidate_trend_state_vector,
  tradability_and_risk_vector
)
  -> candidate_parameter_surface

optional_scalar_projection(candidate_parameter_surface)
  -> candidate_selection_parameter
```

The scalar projection is allowed for sorting, dashboards, and downstream selection, but the durable output must retain supporting context.

### 5. Loss / error measure

Construction loss should not be a simple future-return regression loss. Wrongness is measured by whether the parameter surface identifies tradable, stable, high-certainty candidates without hindsight.

Candidate error/evaluation measures:

- poor rank calibration against forward return/risk labels;
- high selected-candidate drawdown or adverse excursion;
- unstable candidate ranks under small window/config changes;
- high turnover with little added forward evidence;
- selection of illiquid, unoptionable, stale-holding, or event-blocked names;
- weak monotonic relationship between parameter deciles and later tradability/outcome quality;
- leakage or timestamp violations.

### 6. Training / parameter update

V1 should start as interpretable, point-in-time parameter construction rather than a black-box selector:

- reviewed sector/industry ETF universe;
- explicit holdings exposure rules and staleness policy;
- rolling/expanding standardization for relative strength, trend, volatility, and liquidity evidence;
- reviewed eligibility gates for liquidity, optionability, event proximity, stale data, and ambiguity;
- optional learned weights only after walk-forward evidence proves a benefit.

Updates must be chronological. Holdings revisions, late provider updates, and event timestamps must be represented by `available_time`, not hindsight membership.

### 7. Validation / usefulness

Validation should prove that Model 2 improves the candidate pool handed to later layers.

Minimum checks:

- point-in-time holdings and feature availability;
- candidate coverage by source: ETF-holdings-driven vs full-market scan;
- rank/parameter stability through time;
- decile/quantile analysis of `candidate_selection_parameter` vs future return, drawdown, volatility, MFE/MAE, and liquidity outcomes;
- event/liquidity/optionability gate precision and false-reject review;
- comparison to simple baselines such as broad-market top momentum, sector ETF top relative strength, and full-market raw return rank;
- downstream usefulness for `StrategySelectionModel` without leaking strategy results into Model 2 construction.

### 8. Overfitting control

Controls:

- chronological split or walk-forward evaluation;
- no future returns, future ETF holdings, future index membership, or future event interpretations in features;
- sector/industry ETF candidate universe fixed by reviewed eligibility rules, not post-hoc winners;
- full support context retained instead of only a scalar score;
- limited candidate gates and parameter components at V1;
- stability checks across rebalance windows, lookbacks, and liquidity thresholds;
- explicit treatment of stale/missing holdings and survivorship bias;
- forward labels used only for evaluation/calibration.

### 9. Decision deployment

Layer 2 output enters the decision stack as the candidate universe and candidate parameter surface:

```text
SecuritySelectionModel
  -> eligible/watch/gated/excluded ETF and stock candidates
  -> candidate parameter surface and reasons
  -> StrategySelectionModel candidate input
  -> TradeQualityModel candidate signal input
  -> unified decision record candidate-selection audit section
```

Layer 2 does not choose entry timing, strategy family, option contract, final size, execution style, or portfolio approval. Those belong to later layers.

## Remaining Layer Decomposition Queue

The same nine-part decomposition still needs to be completed for:

1. `StrategySelectionModel` — strategy-component composition and compatibility.
2. `TradeQualityModel` — trade outcome distribution, target/stop, MFE/MAE, and horizon.
3. `OptionExpressionModel` — stock/ETF/long-call/long-put expression and contract constraints.
4. `EventOverlayModel` — scheduled/breaking event risk and abnormal-activity overlays.
5. `PortfolioRiskModel` — final offline sizing, exposure, execution-style, exit, and kill-switch gate.

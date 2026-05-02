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

Status: draft updated for review on 2026-05-01.

Layer 2 V1 is a **sector/industry selection model**, not a stock-selection model. Its job is to identify which sector/industry baskets are easiest to trade now: clear leadership, persistent trend, high certainty, enough breadth, acceptable volatility/liquidity, and no obvious event/risk disqualification.

Individual stocks remain the real tradable objects, but selecting a stock before choosing a compatible strategy is premature. Stock-level holdings and exposure data are retained as supporting evidence and a bridge for later layers, not as a Layer 2 V1 output target.

### 1. Data

Primary model-facing inputs:

```text
trading_data.feature_02_security_selection
source_02_security_selection # cleaned sector/industry ETF holdings source rows
stock_etf_exposure           # source-backed evidence for sector composition/transmission, not a stock-selection target
model_01_market_regime       # background/audit/coarse gating only, not direct ranking input
```

ETF holdings are source-side evidence: issuer-published holdings enter through the ETF holdings feed and are cleaned into `source_02_security_selection` rows. `stock_etf_exposure` is downstream of those source rows: a source-backed aggregation that can explain what stocks compose a sector/industry basket and which later stock-level searches may be relevant.

For Layer 2 V1, ETF holdings/exposure answer:

- what the sector/industry ETF actually represents;
- whether the basket is concentrated, diversified, liquid, stale, or compositionally fragile;
- which stocks may later be inspected by `StrategySelectionModel` and later layers.

They do **not** make Layer 2 choose final stocks.

`feature_02_security_selection` is the Layer 2 home for the evidence moved out of `feature_01_market_regime` when Layer 1 was narrowed to broad market properties. Its V1 scope is:

- candidate-comparison rows for reviewed relative-strength combinations with `combination_type in {sector_rotation, daily_context}`;
- one per-snapshot `sector_rotation_summary` row for sector-observation breadth and dispersion aggregates;
- row key: `snapshot_time + candidate_symbol + comparison_symbol + rotation_pair_id` where `candidate_symbol` is the compared sector/industry/daily-context ETF, not an individual stock target;
- payload: relative-strength returns, normalized trend distance/slope/spread/alignment, volatility-ratio, correlation, and sector-observation participation/dispersion evidence.

Eligible evidence:

- sector/industry ETF relative strength, trend, persistence, volatility stability, breadth, dispersion, and signal agreement from the migrated Feature 1 rotation surface;
- point-in-time sector/industry ETF holdings snapshots for composition and transmission diagnostics;
- sector/industry ETF liquidity, spread, volume, gap, volatility, and trend evidence;
- ETF optionability summaries if the sector/industry ETF itself may be traded or used as an options proxy;
- event exclusions that affect the sector/industry basket or make the basket temporarily hard to trade;
- Layer 1 market-property vector only as background, audit context, or coarse no-trade/risk filter.

Excluded from construction:

- individual stock selection as a V1 Layer 2 output;
- future returns as ranking inputs;
- strategy performance;
- option-contract outcomes;
- portfolio PnL;
- broad/macro ETF candidates that do not represent tradable equity sector/industry baskets.

### 2. Features

`X` is a point-in-time sector/industry evidence surface keyed by `available_time + sector_or_industry_symbol`.

Core feature blocks:

- `sector_rotation_state_vector` — sector/industry ETF leadership, persistence, breadth support, volatility stability, and agreement;
- `sector_tradability_vector` — liquidity, spread, volume, optionability if applicable, gap/choppiness, and execution difficulty for the ETF/basket;
- `sector_composition_vector` — holdings concentration, top-name dominance, holdings freshness, source coverage, and stock-exposure diagnostics;
- `sector_risk_context_vector` — event density, earnings concentration, abnormal activity, and macro shock sensitivity for the basket;
- `sector_quality_diagnostics` — stale holdings, missing coverage, conflicting signals, low liquidity, or ambiguous rotation.

`stock_etf_exposure` is a diagnostic/supporting block here, not a row target. It can explain sector composition and provide a handoff universe to later layers, but Layer 2 V1 scores the sector/industry basket.

### 3. Prediction target

V1 does not target “highest future return” and does not target “best stock.”

The target is a sector/industry parameter surface describing which sector/industry baskets are easiest and cleanest to trade under current evidence.

Primary output concept:

```text
sector_selection_parameter_surface[available_time, sector_or_industry_symbol]
```

Possible fields:

```text
sector_or_industry_symbol
basket_type                         # sector_etf, industry_etf, theme_etf_if_accepted
sector_rotation_state_vector
sector_tradability_vector
sector_composition_vector
sector_risk_context_vector
trend_clarity_score
trend_persistence_score
relative_strength_consistency_score
breadth_support_score
liquidity_score
optionability_score
event_risk_score
certainty_score
eligibility_state                   # eligible, watch, gated, excluded
sector_selection_parameter          # optional convenience scalar, not sole output
handoff_stock_universe_refs         # optional references for later strategy/security work
selection_reason
```

Forward returns, realized drawdown, future strategy outcomes, and future trade outcomes are labels for evaluation/calibration only.

### 4. Model mapping from X to output

Conceptual mapping:

```text
sector_rotation_model(feature_02_security_selection)
  -> sector_rotation_state_vector[sector_or_industry_etf]

sector_composition_builder(source_02_security_selection, stock_etf_exposure)
  -> sector_composition_vector[sector_or_industry_etf]

sector_tradability_builder(etf_bar_liquidity_optionability_event_evidence)
  -> sector_tradability_vector[sector_or_industry_etf]

parameter_adjuster(
  sector_rotation_state_vector,
  sector_composition_vector,
  sector_tradability_vector,
  sector_risk_context_vector
)
  -> sector_selection_parameter_surface

optional_scalar_projection(sector_selection_parameter_surface)
  -> sector_selection_parameter
```

The scalar projection is allowed for sorting, dashboards, and downstream routing, but the durable output must retain supporting context.

### 5. Loss / error measure

Construction loss should not be a simple future-return regression loss. Wrongness is measured by whether the selected sector/industry baskets are actually cleaner, more persistent, easier to trade, and more useful to downstream strategy selection than alternatives.

Sector error/evaluation measures:

- poor rank calibration against forward sector/industry return-risk labels;
- high selected-basket drawdown, adverse excursion, or volatility shock;
- unstable sector ranks under small window/config changes;
- high turnover with little added forward evidence;
- selection of illiquid, unoptionable, stale-holding, event-dense, or compositionally fragile baskets;
- weak monotonic relationship between parameter deciles and later sector-level tradability/outcome quality;
- poor downstream usefulness for `StrategySelectionModel`;
- leakage or timestamp violations.

### 6. Training / parameter update

V1 should start as interpretable, point-in-time parameter construction rather than a black-box selector:

- reviewed sector/industry ETF universe;
- explicit holdings freshness, concentration, and coverage diagnostics;
- rolling/expanding standardization for relative strength, trend, volatility, and liquidity evidence;
- reviewed eligibility gates for liquidity, optionability, event proximity, stale data, and ambiguity;
- optional learned weights only after walk-forward evidence proves a benefit.

Updates must be chronological. Holdings revisions, late provider updates, and event timestamps must be represented by `available_time`, not hindsight membership.

### 7. Validation / usefulness

Validation should prove that Model 2 improves the sector/industry context handed to `StrategySelectionModel`.

Minimum checks:

- point-in-time feature, holdings, and event availability;
- sector/industry universe coverage and missing-data diagnostics;
- rank/parameter stability through time;
- decile/quantile analysis of `sector_selection_parameter` vs future sector return, drawdown, volatility, MFE/MAE, liquidity, and tradability outcomes;
- event/liquidity/optionability gate precision and false-reject review;
- comparison to simple baselines such as broad-market top momentum, raw sector ETF relative strength, and equal-weight sector rotation;
- downstream usefulness for `StrategySelectionModel` without leaking strategy results into Model 2 construction.

### 8. Overfitting control

Controls:

- chronological split or walk-forward evaluation;
- no future returns, future ETF holdings, future index membership, or future event interpretations in features;
- sector/industry ETF universe fixed by reviewed eligibility rules, not post-hoc winners;
- full support context retained instead of only a scalar score;
- limited gates and parameter components at V1;
- stability checks across rebalance windows, lookbacks, and liquidity thresholds;
- explicit treatment of stale/missing holdings and survivorship bias;
- forward labels used only for evaluation/calibration.

### 9. Decision deployment

Layer 2 output enters the decision stack as sector/industry context, not final stock selection:

```text
SecuritySelectionModel
  -> eligible/watch/gated/excluded sector/industry baskets
  -> sector selection parameter surface and reasons
  -> optional stock-exposure/handoff references for later inspection
  -> StrategySelectionModel sector-context input
  -> unified decision record sector-selection audit section
```

Layer 2 does not choose final stock, entry timing, strategy family, option contract, final size, execution style, or portfolio approval. Those belong to later layers.

## Remaining Layer Decomposition Queue

## Cross-Layer Separation Principle

The seven-layer stack must keep three contexts separate:

```text
Layer 1: broad market background
Layer 2: sector/industry background
Layer 3+: target subject and strategy-aware trade construction
```

Boundary rules:

- broad market background describes the environment; it must not select sectors or symbols;
- sector/industry background describes where conditions are easiest to trade; it must not finalize stock targets;
- target subject selection is strategy-aware: the tradable symbol only becomes meaningful once the strategy family, signal horizon, liquidity/option expression, event overlay, and portfolio constraints are considered;
- ETF holdings and `stock_etf_exposure` bridge sector composition into later target work, but they do not collapse Layer 2 into stock selection.

The same nine-part decomposition still needs to be completed for:

1. `StrategySelectionModel` — strategy-component composition and compatibility.
2. `TradeQualityModel` — trade outcome distribution, target/stop, MFE/MAE, and horizon.
3. `OptionExpressionModel` — stock/ETF/long-call/long-put expression and contract constraints.
4. `EventOverlayModel` — scheduled/breaking event risk and abnormal-activity overlays.
5. `PortfolioRiskModel` — final offline sizing, exposure, execution-style, exit, and kill-switch gate.

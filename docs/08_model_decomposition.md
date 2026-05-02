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

It must not directly rank sectors, ETFs, or stocks. It also must not pre-assign ETF or sector attributes such as "growth", "defensive", "inflation hedge", or "risk-off beneficiary" as model conclusions. Those relationships must be inferred in Layer 2 from point-in-time behavior, holdings, and market-state-conditioned trend stability.

`SecuritySelectionModel` owns sector/industry rotation, ETF attribute discovery, and candidate parameter surfaces.

## Layer 2 Decomposition: SecuritySelectionModel

Status: revised first-pass structure accepted for the current design route on 2026-05-02.

Layer 2 V1 is an **ETF/sector attribute discovery and sector/industry trend-stability model**. It is not a stock selector and not a hand-written sector-style classifier.

Its core question is:

> Given the current and historical broad market context, which sector/industry ETF baskets exhibit stable, tradable trend behavior, and what attributes does the data imply for each basket?

Here, stability means **trend stability**, not price stability: persistent one-way advance/decline, clean directional continuation, orderly pullback-resumption, persistent breakdown, or clear repeatable cyclicality. Random chop, repeated false breaks, and inconsistent reaction to similar market states are unstable even if price volatility is low.

### 1. Data

Primary model-facing inputs:

```text
model_01_market_regime       # broad market context state, conditioning input only
trading_data.feature_02_security_selection
source_02_security_selection # cleaned sector/industry ETF holdings source rows
stock_etf_exposure           # source-backed composition/transmission evidence, not a stock-selection target
ETF/liquidity/optionability/event evidence
```

Layer 1 input is used only as market context. It must not provide pre-labeled ETF attributes. For example, Layer 2 should not receive conclusions like `technology = growth`, `utilities = defensive`, or `gold = safe_haven` as fixed truth. If such labels are useful, they are optional post-fit interpretations of Layer 2 evidence.

`feature_02_security_selection` is the Layer 2 home for sector/industry rotation and daily-context evidence moved out of Layer 1. Its V1 physical row shape remains the accepted comparison surface:

- candidate-comparison rows for reviewed relative-strength combinations with `combination_type in {sector_rotation, daily_context}`;
- one per-snapshot `sector_rotation_summary` row for sector-observation breadth and dispersion aggregates;
- row key: `snapshot_time + candidate_symbol + comparison_symbol + rotation_pair_id` where `candidate_symbol` is the compared ETF/basket, not a stock target;
- payload: relative-strength returns, normalized trend distance/slope/spread/alignment, volatility-ratio, correlation, and sector-observation participation/dispersion evidence.

ETF holdings and `stock_etf_exposure` answer what each basket contains and how concentrated/fresh/fragile that composition is. They also create downstream handoff references for anonymous target-candidate construction. They do **not** make Layer 2 choose final stocks.

Eligible evidence:

- broad market context from `model_01_market_regime` as a conditioning variable;
- sector/industry ETF relative strength, trend, persistence, cyclicality, volatility-of-trend, breadth, dispersion, and signal agreement;
- point-in-time ETF holdings, concentration, top-name dominance, holdings freshness, and exposure overlap;
- ETF liquidity, spread, volume, gap behavior, optionability, event density, and abnormal activity;
- inferred ETF/sector attributes learned from point-in-time behavior and holdings.

Excluded from construction:

- hard-coded ETF behavior classes such as growth/defensive/cyclical/safe-haven;
- individual stock selection as a V1 Layer 2 output;
- future returns as ranking inputs;
- strategy performance;
- option-contract outcomes;
- portfolio PnL.

### 2. Features

`X` is a point-in-time sector/industry evidence surface keyed by:

```text
available_time + sector_or_industry_symbol
```

Core feature blocks:

```text
market_context_state
sector_observed_behavior_vector
sector_market_condition_profile
sector_trend_stability_vector
sector_attribute_vector
sector_composition_vector
sector_tradability_vector
sector_risk_context_vector
sector_quality_diagnostics
```

Definitions:

- `market_context_state` — Layer 1 broad market state, used as conditioning context only.
- `sector_observed_behavior_vector` — observed sector/industry ETF behavior: relative strength, trend direction, trend clarity, trend persistence, breadth support, volatility-of-trend, correlation, and dispersion.
- `sector_market_condition_profile` — how the basket behaves under different broad market states; e.g. which market contexts historically produce clean trends, chop, reversals, or cycles.
- `sector_trend_stability_vector` — directional persistence, monotonicity, pullback regularity, breakdown persistence, cycle regularity, false-break frequency, and choppiness.
- `sector_attribute_vector` — inferred, evidence-backed ETF/sector attributes. This may later include human-readable interpretations, but the model-facing vector is behavioral and point-in-time.
- `sector_composition_vector` — holdings concentration, top-name dominance, holdings freshness, source coverage, overlap/crowding, and stock-exposure diagnostics.
- `sector_tradability_vector` — ETF/basket liquidity, spread, volume, optionability, gap/choppiness, and execution difficulty.
- `sector_risk_context_vector` — event density, earnings concentration, abnormal activity, macro shock sensitivity, and known no-trade states.
- `sector_quality_diagnostics` — stale holdings, missing coverage, conflicting signals, low liquidity, sparse history, or ambiguous rotation.

### 3. Prediction target

V1 does not target “highest future return” and does not target “best stock.”

The target is a sector/industry state and parameter surface describing:

1. what attributes the ETF/sector currently exhibits;
2. in which broad market contexts its trend tends to be stable;
3. whether it is currently easy enough to pass downstream for strategy-aware anonymous target work.

Primary output concept:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Possible fields:

```text
sector_or_industry_symbol
basket_type
sector_attribute_vector
sector_market_condition_profile
sector_trend_stability_vector
trend_direction_state              # advance / decline / range / transition / mixed
trend_stability_state              # stable_directional / stable_cyclical / choppy / false_break_prone / unstable
trend_stability_score
cycle_regularity_score
relative_strength_consistency_score
breadth_support_score
composition_quality_score
liquidity_score
optionability_score
event_risk_score
certainty_score
eligibility_state                  # eligible / watch / gated / excluded
sector_selection_parameter         # optional routing scalar, not sole output
handoff_stock_universe_refs        # optional references for later anonymous target construction
selection_reason
```

Forward returns, future drawdown, future trend-stability labels, and future strategy outcomes are evaluation/calibration labels only.

### 4. Model mapping from X to output

Conceptual mapping:

```text
observed_behavior_builder(feature_02_security_selection)
  -> sector_observed_behavior_vector

market_condition_stability_model(
  model_01_market_regime,
  sector_observed_behavior_vector
)
  -> sector_market_condition_profile
  -> sector_trend_stability_vector

sector_composition_builder(source_02_security_selection, stock_etf_exposure)
  -> sector_composition_vector

sector_tradability_builder(etf_liquidity_optionability_event_evidence)
  -> sector_tradability_vector

attribute_discovery_model(
  sector_observed_behavior_vector,
  sector_market_condition_profile,
  sector_composition_vector,
  sector_tradability_vector,
  sector_risk_context_vector
)
  -> sector_attribute_vector

parameter_adjuster(
  sector_attribute_vector,
  sector_market_condition_profile,
  sector_trend_stability_vector,
  sector_composition_vector,
  sector_tradability_vector,
  sector_risk_context_vector,
  sector_quality_diagnostics
)
  -> sector_context_state
  -> optional sector_selection_parameter
```

The scalar projection is allowed for dashboards and routing, but the durable output is the full context state.

### 5. Loss / error measure

Wrongness is measured by whether inferred sector attributes and stability states are point-in-time, stable under refits, and useful downstream.

Evaluation/error measures:

- sector trend-stability calibration by market context;
- false-break / chop rate after an `eligible` state;
- directional persistence after stable-directional states;
- cycle regularity after stable-cyclical states;
- rank/parameter stability under small lookback/config changes;
- selection of illiquid, unoptionable, stale-holding, event-dense, or compositionally fragile baskets;
- weak monotonic relationship between parameter deciles and future trend stability/tradability;
- poor downstream usefulness for anonymous target/strategy selection;
- leakage or timestamp violations.

### 6. Training / parameter update

V1 should start as interpretable, point-in-time state construction:

- reviewed sector/industry ETF universe;
- no hard-coded ETF behavior labels;
- rolling/expanding standardization for sector behavior evidence;
- market-state-conditioned behavior tables/profiles;
- explicit holdings freshness, concentration, overlap, and coverage diagnostics;
- reviewed gates for liquidity, optionability, event proximity, stale data, and ambiguity;
- optional learned weights or clustering only after walk-forward evidence proves a benefit.

Updates must be chronological. Holdings revisions, late provider updates, market-state revisions, and event timestamps must be represented by `available_time`, not hindsight membership.

### 7. Validation / usefulness

Validation should prove that Layer 2 adds useful sector context for downstream anonymous target and strategy selection.

Minimum checks:

- point-in-time feature, holdings, event, and market-context availability;
- no pre-assigned ETF behavior labels in model-facing inputs;
- sector/industry universe coverage and missing-data diagnostics;
- stability of inferred `sector_attribute_vector` and `sector_trend_stability_vector` through time;
- decile/quantile analysis of `sector_selection_parameter` vs future trend stability, directional persistence, cycle regularity, false-break frequency, drawdown, volatility, liquidity, and tradability outcomes;
- comparison to baselines: raw sector ETF momentum, equal-weight sector rotation, and market-context-agnostic sector ranking;
- downstream usefulness for anonymized `StrategySelectionModel` without leaking strategy results into Layer 2 construction.

### 8. Overfitting control

Controls:

- chronological split or walk-forward evaluation;
- no future returns, future ETF holdings, future index membership, future sector labels, or future event interpretations in features;
- no hand-coded behavior labels as hidden priors;
- sector/industry ETF universe fixed by reviewed eligibility rules, not post-hoc winners;
- full support context retained instead of only a scalar score;
- limited gates and parameter components at V1;
- stability checks across market-context buckets, rebalance windows, lookbacks, and liquidity thresholds;
- explicit treatment of stale/missing holdings and survivorship bias;
- forward labels used only for evaluation/calibration.

### 9. Decision deployment

Layer 2 output enters the decision stack as sector/industry context:

```text
SecuritySelectionModel
  -> sector_context_state
  -> inferred sector_attribute_vector
  -> sector_market_condition_profile
  -> sector_trend_stability_vector
  -> eligible/watch/gated/excluded sector/industry baskets
  -> optional handoff_stock_universe_refs for anonymous target-candidate construction
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
- sector/industry background describes where conditions are easiest to trade and in which broad-market states sector trends are stable; it must not finalize stock targets;
- target subject selection is strategy-aware and identity-neutral: the tradable symbol only becomes meaningful once the strategy family, signal horizon, liquidity/option expression, event overlay, and portfolio constraints are considered; target models should consume anonymized candidate feature vectors rather than memorize tickers;
- ETF holdings and `stock_etf_exposure` bridge sector composition into later target work, but they do not collapse Layer 2 into stock selection.

The same nine-part decomposition still needs to be completed for:

1. `StrategySelectionModel` — strategy-component composition and compatibility.
2. `TradeQualityModel` — trade outcome distribution, target/stop, MFE/MAE, and horizon.
3. `OptionExpressionModel` — stock/ETF/long-call/long-put expression and contract constraints.
4. `EventOverlayModel` — scheduled/breaking event risk and abnormal-activity overlays.
5. `PortfolioRiskModel` — final offline sizing, exposure, execution-style, exit, and kill-switch gate.

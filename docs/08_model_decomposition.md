# Model Decomposition Framework

Status: current design spine
Owner intent: every model layer must have the same reviewable nine-part decomposition before implementation or promotion expands.

## Nine-Part Structure

For each layer, define:

1. **Data** — eligible point-in-time input tables/artifacts, owner, and availability timestamp.
2. **Features** — model-facing `X`, diagnostic fields, evaluation-only fields, and intentionally unused fields.
3. **Prediction target** — supervised target, rank objective, inferred latent state, or parameter surface.
4. **Model mapping** — how `X` becomes the output state/vector/ranker/gate.
5. **Loss / error measure** — how wrongness is measured during fitting, scoring, calibration, or evaluation.
6. **Training / parameter update** — how scalers, thresholds, rules, or learned parameters update without leakage.
7. **Validation / usefulness** — how the layer proves decision usefulness, not just historical fit.
8. **Overfitting control** — how the layer avoids hindsight, data snooping, unstable refits, and false confidence.
9. **Decision deployment** — how the output enters the offline decision record and downstream gates.

## Cross-Layer Rules

- Every row must be point-in-time and keyed by a timestamp genuinely knowable to the system.
- Data acquisition/source evidence stays in `trading-data`.
- Global terms, fields, artifacts, statuses, templates, and contracts route through `trading-manager`.
- Do not collapse rich context into a scalar unless supporting fields remain available for audit and downstream interpretation.
- Live/paper order mutation remains outside `trading-model`.

## Layer 1: MarketRegimeModel

Status: accepted V1 contract.

### 1. Data

Primary input:

```text
trading_data.feature_01_market_regime
```

Eligible evidence: broad-market, cross-asset, credit/rate/dollar/commodity, volatility, breadth, correlation, concentration, trend, liquidity/funding, sentiment/risk-appetite, and market-structure signals available at or before `available_time`.

Excluded construction inputs: sector/industry rotation conclusions, ETF/sector behavior labels, selected securities, strategy performance, option-contract outcomes, portfolio PnL, and future-return labels.

### 2. Features

`X` is the point-in-time feature vector from `feature_01_market_regime`.

Evidence roles:

| Role | Meaning |
|---|---|
| primary evidence | Directly supports a market-property factor and participates in construction. |
| diagnostic evidence | Explains, stress-tests, or sanity-checks a factor without directly driving it. |
| quality evidence | Supports coverage, freshness, reliability, or `data_quality_score`. |
| evaluation-only evidence | Used only after output construction to test usefulness. |
| intentionally unused evidence | Excluded with a documented reason. |

Feature groups should map to the current market-property factors:

```text
price_behavior_factor
trend_certainty_factor
capital_flow_factor
sentiment_factor
valuation_pressure_factor
fundamental_strength_factor
macro_environment_factor
market_structure_factor
risk_stress_factor
transition_pressure
data_quality_score
```

Layer 1 evidence maturation means maintaining the feature-to-factor evidence map in `src/models/model_01_market_regime/evidence_map.md`. It does not mean adding sector/ETF/stock conclusions to Layer 1.

### 3. Prediction target

V1 has no supervised target and no required regime label.

Physical output:

```text
trading_model.model_01_market_regime
```

Conceptual output:

```text
market_context_state
```

Future returns may be used only as evaluation labels.

### 4. Model mapping

Current V1 mapping:

```text
rolling/expanding point-in-time scaler
  -> per-signal z-score with clipping/floors
  -> reviewed sign direction
  -> factor-level reducer
  -> bounded continuous factor values
  -> transition_pressure + data_quality_score
```

No current or future row may fit the scaler for the row being scored.

### 5. Loss / error measure

V1 is unsupervised. Wrongness is reviewed through:

- leakage/timestamp violations;
- missing or low signal coverage;
- factor instability under rolling/expanding refits;
- unintuitive sign behavior against reviewed evidence;
- weak explanatory value for Layer 2 sector trend stability;
- weak usefulness for option-expression constraints or portfolio-risk policy.

### 6. Training / parameter update

Current parameters are reviewed configuration and rolling state:

- factor membership and signs in config;
- lookback, minimum history, floors, z-score clipping, reducers, and coverage thresholds explicit;
- rolling/expanding statistics update only from prior available rows;
- config changes require tests and acceptance evidence.

### 7. Validation / usefulness

Minimum validation:

- chronological splits;
- factor distribution checks;
- rolling/refit stability checks;
- feature-to-factor evidence-map review against `src/models/model_01_market_regime/evidence_map.md`;
- downstream explanatory tests against a market-context-free Layer 2 baseline;
- option-expression usefulness checks for DTE/delta/IV/theta/no-trade policy;
- portfolio-risk usefulness checks for drawdown, exposure, sizing, execution-style, exit, and kill-switch policy.

### 8. Overfitting control

Controls:

- no future labels in construction;
- limited factor count;
- reviewed feature membership;
- bounded/clipped values;
- minimum signal coverage;
- config-driven formulas;
- promotion gate based on evaluation evidence.

### 9. Decision deployment

Layer 1 is broad market background:

```text
model_01_market_regime
  -> market_context_state
  -> Layer 2 sector trend-stability conditioning
  -> strategy compatibility context
  -> option-expression constraints
  -> portfolio-risk policy
  -> decision-record audit context
```

It must not directly rank sectors, ETFs, or stocks and must not pre-assign ETF/sector attributes.

## Layer 2: SecuritySelectionModel

Status: accepted design route; implementation pending.

Layer 2 V1 is an ETF/sector attribute discovery and sector/industry trend-stability model. It is not a stock selector and not a hand-written sector-style classifier.

### 1. Data

Primary inputs:

```text
market_context_state                 # Layer 1, conditioning only
trading_data.feature_02_security_selection
source_02_security_selection         # ETF holdings source rows
stock_etf_exposure                   # composition/transmission evidence
ETF liquidity / optionability / event evidence
```

Layer 1 input must not provide pre-labeled ETF attributes. Labels such as `growth`, `defensive`, `cyclical`, or `safe_haven` are optional post-fit interpretations, not input truth.

### 2. Features

`X` is keyed by:

```text
available_time + sector_or_industry_symbol
```

Core blocks:

```text
market_context_state
sector_observed_behavior_vector
sector_attribute_vector
sector_market_condition_profile
sector_trend_stability_vector
sector_composition_vector
sector_tradability_vector
sector_risk_context_vector
sector_quality_diagnostics
```

### 3. Prediction target

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Core output blocks:

```text
sector_observed_behavior_vector
sector_attribute_vector
sector_market_condition_profile
sector_trend_stability_vector
sector_composition_vector
sector_tradability_vector
sector_risk_context_vector
eligibility_state
optional sector_selection_parameter
optional handoff_stock_universe_refs
```

The target is clean, persistent, understandable sector/industry trend behavior under market context, not highest future return and not final stock selection.

### 4. Model mapping

V1 mapping should combine:

```text
sector behavior evidence
  + market-context conditioning
  + inferred attribute discovery
  + trend stability / cycle regularity scoring
  + composition / tradability / risk diagnostics
  -> sector_context_state
```

### 5. Loss / error measure

Evaluate wrongness through:

- trend persistence/cycle stability errors;
- false-break and chop misclassification;
- poor calibration under similar market contexts;
- low downstream strategy usefulness;
- unstable inferred attributes;
- liquidity/optionability/event gate misses.

Future returns can evaluate usefulness but must not become direct production ranking inputs.

### 6. Training / parameter update

Use chronological/walk-forward updates. Refit sector profiles only with information available by each evaluation time. Attribute labels, if shown to humans, are post-fit interpretations and should be versioned with the model/config.

### 7. Validation / usefulness

Layer 2 must prove:

- sector trend-stability separation;
- calibration by market context;
- improved downstream strategy-candidate quality versus context-free sector ranking;
- stable inferred attributes across refits;
- no final-stock leakage;
- no hard-coded style-label dependence.

### 8. Overfitting control

Controls:

- limit eligible baskets to reviewed sector/industry equity ETFs;
- avoid hand-written style labels as training truth;
- separate production features from evaluation labels;
- require liquidity/optionability/event gates;
- keep `stock_etf_exposure` as composition evidence, not stock target selection.

### 9. Decision deployment

Layer 2 output feeds downstream target and strategy work:

```text
sector_context_state
  -> anonymous target candidate builder
  -> StrategySelectionModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> PortfolioRiskModel
```

It may provide `handoff_stock_universe_refs`, but final stock choice waits for strategy-aware downstream layers.

## Anonymous Target Candidate Builder

Status: required boundary; detailed contract pending.

Purpose: create anonymous model-facing candidate rows for Layer 3+ while preserving real symbol references for audit/routing only.

Required separation:

```text
model-facing:  target_candidate_id + anonymous_target_feature_vector
metadata:      audit_symbol_ref + routing_symbol_ref
```

The model-facing vector may include target behavior, liquidity/tradability, market context, sector context, event/risk context, cost, and strategy-compatibility features. It must exclude raw ticker/company identity.

## Layer 3: StrategySelectionModel

Status: decomposition pending.

Must compose strategy components for anonymous target candidates. It should output strategy fit, component weights, disabled-strategy reasons, parameter-neighborhood stability, and robustness evidence.

## Layer 4: TradeQualityModel

Status: decomposition pending.

Must estimate trade outcome quality, expected move, target/stop, MFE/MAE, and holding horizon under selected strategy context.

## Layer 5: OptionExpressionModel

Status: decomposition pending.

V1 is direct stock/ETF comparison plus long call / long put only. It must use timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, and market-context constraints.

## Layer 6: EventOverlayModel

Status: decomposition pending.

Must preserve event timing and source priority. It can adjust earlier layers and risk based on scheduled events, breaking news, abnormal activity, and event-memory evidence.

## Layer 7: PortfolioRiskModel

Status: decomposition pending.

Final offline risk gate for exposure, sizing, execution-style policy, exit lifecycle, drawdown state, correlation, liquidity, and kill-switch behavior. It does not place orders.

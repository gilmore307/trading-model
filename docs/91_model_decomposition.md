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

### Model artifact split

Each implemented model layer should separate three artifact classes:

```text
model_NN_<layer_slug>                 # output
model_NN_<layer_slug>_explainability  # human review/debug/explain
model_NN_<layer_slug>_diagnostics     # acceptance/monitoring/gating
```

Primary `model` outputs stay narrow and stable. Explainability and diagnostics may be wider, but downstream production logic should not hard-depend on them without a reviewed promotion decision.

Layer-owned fields use compact `1_*`, `2_*`, ... prefixes consistently across docs, model-facing payloads, and SQL physical columns. SQL writers quote numeric-leading names where required rather than inventing `layer01_*` / `layer02_*` aliases.

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
| quality evidence | Supports coverage, freshness, reliability, or `1_data_quality_score`. |
| evaluation-only evidence | Used only after output construction to test usefulness. |
| intentionally unused evidence | Excluded with a documented reason. |

Feature groups should map to the current model-facing market-property keys:

```text
1_price_behavior_factor
1_trend_certainty_factor
1_capital_flow_factor
1_sentiment_factor
1_valuation_pressure_factor
1_fundamental_strength_factor
1_macro_environment_factor
1_market_structure_factor
1_risk_stress_factor
1_transition_pressure
1_data_quality_score
```

When persisted to SQL, these `1_*` model-facing keys remain the physical column names. SQL writers should quote numeric-leading identifiers where required instead of creating `layer01_*` aliases.

Layer 1 evidence maturation means maintaining the feature-to-factor evidence map in `src/models/model_01_market_regime/evidence_map.md`. It does not mean adding sector/ETF/stock conclusions to Layer 1.

### 3. Prediction target

V1 has no supervised target and no required regime label.

Physical artifacts:

```text
trading_model.model_01_market_regime
trading_model.model_01_market_regime_explainability
trading_model.model_01_market_regime_diagnostics
```

The primary output carries the narrow downstream market-context state. Reviewed per-factor attribution context, evidence-role refs, and config/factor spec refs belong to `model_01_market_regime_explainability`; detailed source-contribution and bucket-score rows may be added there only when a reviewed implementation needs them. Missingness/freshness, minimum-history, standardization, z-score clipping, feature coverage, data-quality decomposition, chronological split/refit stability, downstream usefulness, baseline comparison, and no-future-leak checks belong to `model_01_market_regime_diagnostics`.

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
  -> 1_transition_pressure + 1_data_quality_score
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

## Layer 2: SectorContextModel

Status: accepted design route; implementation pending.

Layer 2 V1 is an ETF/sector attribute discovery and sector/industry trend-stability model. It is not a stock selector and not a hand-written sector-style classifier.

### 1. Data

Primary inputs:

```text
market_context_state                 # Layer 1, conditioning only
trading_data.feature_02_sector_context
ETF liquidity / optionability / event evidence
```

Layer 1 input must not provide pre-labeled ETF attributes. Labels such as `growth`, `defensive`, `cyclical`, or `safe_haven` are optional post-fit interpretations, not input truth.

Layer 1 market-property factors are conditioning context only. Layer 2 should build a distinct `2_sector_conditional_behavior_vector` that describes how each ETF/basket behaves under similar market backgrounds; it should not reuse Layer 1 factor names as ETF style fields.

The conditional behavior vector should prefer signed axes: for example, positive/negative values on one axis can represent with-market versus inverse direction, volatility amplification versus dampening, upside-favorable versus downside-heavy capture, or context tailwind versus headwind.

### 2. Features

`X` is keyed by:

```text
available_time + sector_or_industry_symbol
```

Core blocks:

```text
market_context_state
2_sector_observed_behavior_vector
2_sector_attribute_vector
2_sector_conditional_behavior_vector
2_sector_trend_stability_vector
2_sector_tradability_vector
2_sector_risk_context_vector
2_sector_quality_diagnostics
```

### 3. Prediction target

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Planned physical artifacts:

```text
trading_model.model_02_sector_context
trading_model.model_02_sector_context_explainability
trading_model.model_02_sector_context_diagnostics
```

The V1 field contract is owned by `src/models/model_02_sector_context/sector_context_state_contract.md`.

Primary output keeps only the narrow downstream dependency surface: identity, trend/context stability state, downstream sector handoff, and eligibility/quality summary. Observed behavior, inferred attributes, conditional behavior internals, contributing evidence, and reason-code detail belong to `model_02_sector_context_explainability`. Liquidity/spread/optionability, event/gap/volatility/correlation stress, freshness/missingness, baseline comparison, refit stability, and no-future-leak evidence belong to `model_02_sector_context_diagnostics`.

When persisted to SQL, `2_*` model-facing keys remain the physical column names. SQL writers should quote numeric-leading identifiers where required instead of creating `layer02_*` aliases.

The target is clean, persistent, understandable sector/industry trend behavior under market context, not highest future return and not final stock selection. Layer 2 may select/prioritize sector baskets for downstream candidate construction, but it does not expand them into stock candidates.

### 4. Model mapping

V1 mapping should combine:

```text
sector behavior evidence
  + market-context conditioning for similar-background comparison
  + distinct conditional behavior vector learning
  + inferred attribute discovery
  + trend stability / cycle regularity scoring
  + tradability / risk diagnostics
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
- no hard-coded style-label dependence;
- conformance to `src/models/model_02_sector_context/sector_context_state_contract.md`.

### 8. Overfitting control

Controls:

- limit eligible baskets to reviewed sector/industry equity ETFs;
- avoid hand-written style labels as training truth;
- separate production features from evaluation labels;
- require liquidity/optionability/event gates;
- keep ETF holdings and `stock_etf_exposure` outside Layer 2 core behavior modeling.

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

It may provide selected/prioritized sector basket handoff state, but stock-universe construction waits for the anonymous target candidate builder.

## Anonymous Target Candidate Builder

Status: contract-first; implementation pending.

Contract owner:

```text
src/models/anonymous_target_candidate_builder/target_candidate_builder_contract.md
```

Purpose: create anonymous model-facing candidate rows for Layer 3+ from Layer 2 selected/prioritized sector baskets while preserving real symbol references for audit/routing only.

Conceptual row shape:

```text
anonymous_target_candidate[available_time, target_candidate_id]
```

Required separation:

```text
model-facing:
  target_candidate_id
  anonymous_target_feature_vector
  market_context_state_ref
  sector_context_state_ref

metadata:
  audit_symbol_ref
  routing_symbol_ref
  source_sector_or_industry_symbol
  source_holding_ref
  source_stock_etf_exposure_ref
```

The candidate builder may use ETF holdings and `stock_etf_exposure` to transmit Layer 2 selected sector/industry baskets into stock candidates. The model-facing vector may include target behavior, liquidity/tradability, market context, sector context, event/risk context, exposure transmission, cost, optionability, and quality evidence. It must exclude raw ticker/company identity and must not let `target_candidate_id` become a categorical fitting feature.

V1 acceptance must prove point-in-time construction, no Layer 2 holdings leakage, recoverable audit/routing metadata, duplicate-candidate handling, and anonymity checks before StrategySelectionModel consumes candidates.

## Layer 3: StrategySelectionModel

Status: draft strategy-family/variant contract pending review.

Contract owner:

```text
docs/04_layer_03_strategy_selection.md
```

Must compose strategy components for anonymous target candidates. It should output strategy family, strategy variant, directional/horizon/setup attributes, fit scores, disabled-strategy reasons, parameter-neighborhood stability, and robustness evidence. It must not output final entry/exit prices, option contracts, position sizes, execution policy, or portfolio allocation.

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

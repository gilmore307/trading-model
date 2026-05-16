# Model Decomposition Framework
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-15): conceptual Layers 4-8 are now Layer 4 AlphaConfidenceModel, Layer 5 PositionProjectionModel, Layer 6 UnderlyingActionModel, Layer 7 TradingGuidanceModel / OptionExpressionModel, and Layer 8 EventRiskGovernor / EventIntelligenceOverlay. Legacy physical paths such as `model_08_event_risk_governor` and `model_08_option_expression` may remain in implementation notes until a dedicated migration renames them.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: accepted Layers 1-8 design spine; model-design phase closed
Owner intent: every model layer must keep the same reviewable nine-part decomposition before production promotion expands.

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
- Use `docs/92_vector_taxonomy.md` as the vocabulary authority: feature surfaces feed models, feature vectors are model-facing inputs, states/state vectors are model outputs, scores are scalar dimensions, labels/outcomes are training/evaluation-only.
- Live/paper order mutation remains outside `trading-model`.

## Layer 1: MarketRegimeModel

Status: accepted V2.2 contract with deterministic implementation/evaluation path; production promotion remains evidence-gated.

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
| primary evidence | Directly supports a public market-context state score and participates in construction. |
| diagnostic evidence | Explains, stress-tests, or sanity-checks a state score without directly driving it. |
| quality evidence | Supports coverage, freshness, reliability, or `1_data_quality_score`. |
| evaluation-only evidence | Used only after output construction to test usefulness. |
| intentionally unused evidence | Excluded with a documented reason. |

Layer 1 feature groups map to separate market-tradability semantic families:

```text
1_market_direction_score
1_market_direction_strength_score
1_market_trend_quality_score
1_market_stability_score
1_market_risk_stress_score
1_market_transition_risk_score
1_breadth_participation_score
1_correlation_crowding_score
1_dispersion_opportunity_score
1_market_liquidity_pressure_score
1_market_liquidity_support_score
1_coverage_score
1_data_quality_score
```

SQL writers should quote numeric-leading identifiers where required instead of creating `layer01_*` aliases.

Layer 1 evidence maturation means maintaining the feature-to-state evidence map in `src/models/model_01_market_regime/evidence_map.md`. It does not mean adding sector/ETF/stock conclusions to Layer 1.

### 3. Prediction target

Layer 1 has no supervised construction target and no required regime label. The conceptual target is current broad-market tradability/regime state: direction evidence, trend quality, stability, risk/stress, transition risk, breadth, correlation/crowding, dispersion opportunity, liquidity pressure/support, coverage, and data quality.

Physical artifacts:

```text
trading_model.model_01_market_regime
trading_model.model_01_market_regime_explainability
trading_model.model_01_market_regime_diagnostics
```

The primary output carries the narrow downstream market-context state. Reviewed per-state attribution context, evidence-role refs, and config refs belong to `model_01_market_regime_explainability`; detailed source-contribution and bucket-score rows may be added there only when a reviewed implementation needs them. Missingness/freshness, minimum-history, standardization, z-score clipping, feature coverage, data-quality decomposition, chronological split/refit stability, downstream usefulness, baseline comparison, and no-future-leak checks belong to `model_01_market_regime_diagnostics`.

Conceptual output:

```text
market_context_state
```

Future returns may be used only as evaluation labels.

### 4. Model mapping

Current mapping:

```text
rolling/expanding point-in-time scaler
  -> per-signal z-score with clipping/floors
  -> reviewed sign direction
  -> internal signal-group reducers
  -> public market-context state scores
  -> explainability + diagnostics support artifacts
```

No current or future row may fit the scaler for the row being scored.

### 5. Loss / error measure

Layer 1 construction is unsupervised. Wrongness is reviewed through:

- leakage/timestamp violations;
- missing or low signal coverage;
- state-score instability under rolling/expanding refits;
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
  -> Layer 2 sector tradability conditioning
  -> Layer 3 target-state context
  -> alpha/confidence and position-projection constraints
  -> option-expression constraints
  -> portfolio-risk policy
  -> decision-record audit context
```

It must not directly rank sectors, ETFs, or stocks and must not pre-assign ETF/sector attributes.

## Layer 2: SectorContextModel

Status: accepted direction-neutral contract with deterministic implementation/evaluation path; production promotion remains evidence-gated.

Layer 2 V1 is an ETF/sector attribute discovery and direction-neutral sector/industry tradability-context model. It is not a stock selector and not a hand-written sector-style classifier.

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

Primary output keeps only the narrow downstream dependency surface: identity, signed sector direction evidence, direction-neutral trend/tradability state, separate handoff state and handoff bias, and eligibility/quality summary. Observed behavior, inferred attributes, conditional behavior internals, contributing evidence, and reason-code detail belong to `model_02_sector_context_explainability`. Liquidity/spread/optionability, event/gap/volatility/correlation stress, freshness/missingness, baseline comparison, refit stability, and no-future-leak evidence belong to `model_02_sector_context_diagnostics`.

When persisted to SQL, `2_*` model-facing keys remain the physical column names. SQL writers should quote numeric-leading identifiers where required instead of creating `layer02_*` aliases.

The target is clean, persistent, understandable, direction-neutral sector/industry tradability behavior under market context, not highest future return, long-only strength, and not final stock selection. Layer 2 may select/prioritize sector baskets for downstream candidate construction, including stable short-bias contexts, but it does not expand them into stock candidates.

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

Layer 2 output feeds downstream target-state work:

```text
sector_context_state
  -> TargetStateVectorModel
     (Layer 3 preprocessing: anonymous target candidate builder)
  -> EventRiskGovernor
  -> AlphaConfidenceModel
  -> PositionProjectionModel
  -> UnderlyingActionModel
  -> OptionExpressionModel
```

It may provide selected/prioritized sector basket handoff state and a separate `long_bias` / `short_bias` / `neutral` / `mixed` handoff bias, but stock-universe construction waits for the anonymous target candidate builder.

### Layer 3 preprocessing: Anonymous Target Candidate Builder

Status: Layer 3 preprocessing sub-boundary; contract plus first deterministic implementation complete. It is not a separate model layer and must not be represented as a peer to `TargetStateVectorModel`.

Contract owner:

```text
src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md
```

Purpose: create anonymous model-facing candidate rows and `anonymous_target_feature_vector` inputs for Layer 3 from Layer 2 selected/prioritized sector baskets while preserving real symbol references for audit/routing only.

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

The candidate builder may use ETF holdings and `stock_etf_exposure` to transmit Layer 2 selected/watch sector/industry baskets into stock candidates. The model-facing `anonymous_target_feature_vector` may include target behavior, liquidity/tradability, anonymous structural buckets, market context, sector context, event/risk context, exposure transmission, cost, optionability, and quality evidence. It is a Layer 3 input feature vector, not the Layer 3 output state vector. It must exclude raw ticker/company identity, stable identity-surrogate bucket combinations, and must not let `target_candidate_id` become a categorical fitting feature.

V1 acceptance must prove point-in-time construction, no Layer 2 holdings leakage, recoverable audit/routing metadata, duplicate-candidate handling, and anonymity checks before TargetStateVectorModel consumes candidates. The current `builder.py` implementation provides deterministic row construction and recursive identity/downstream-field leakage checks; production maturity still depends on real-data evaluation.

## Layer 3: TargetStateVectorModel

Status: accepted target state-vector contract with deterministic implementation/evaluation scaffold complete; production promotion pending real-data evidence and accepted review.

Contract owners:

```text
docs/04_layer_03_target_state_vector.md
src/models/model_03_target_state_vector/target_state_vector_contract.md
```

Must construct a direction-neutral anonymous target state vector by fusing Layer 1 market state, Layer 2 sector state, and target-local tape/liquidity/behavior evidence prepared by Layer 3 preprocessing. The primary `target_context_state` output consists of four inspectable blocks: `market_state_features`, `sector_state_features`, `target_state_features`, and `cross_state_features`. Embedding/cluster outputs may be derived representations, but they must not replace the inspectable blocks. Signed direction evidence, tradability, transition risk, noise, liquidity/cost, and row reliability must remain separate. It must not select strategy families, expand parameter variants, output alpha confidence, output final entry/exit prices, choose option contracts, size positions, define execution policy, or perform portfolio allocation.

## Layer 4: AlphaConfidenceModel

Status: accepted V1 contract with deterministic scaffold complete for the current model-design phase; production promotion remains evidence-gated.

Contract owner:

```text
docs/05_layer_04_alpha_confidence.md
```

Must convert reviewed Layer 1/2/3 state evidence into the final adjusted `alpha_confidence_vector`: alpha direction, alpha strength, expected residual return, confidence, signal reliability, path quality, reversal risk, drawdown risk, and alpha-level tradability. Base/unadjusted alpha from Layer 1/2/3 is retained as diagnostics only; the adjusted vector is the default Layer 5-facing output. Directional alpha belongs here, not in Layer 3. Event intelligence is no longer a hard upstream prerequisite for base alpha; Layer 8 may later intervene on the base guidance. Layer 4 must not project target exposure, select option contracts, size positions, emit final actions, or mutate broker/account state.

## Layer 5: PositionProjectionModel

Status: accepted V1 contract with deterministic scaffold complete for the current model-design phase; production promotion remains evidence-gated.

Contract owner:

```text
docs/06_layer_05_position_projection.md
```

### 1. Data

Primary inputs:

```text
alpha_confidence_vector                 # Layer 4 final adjusted output
current_position_state                  # point-in-time current abstract exposure
pending_position_state                  # point-in-time pending exposure / fill probability
position_level_friction_context          # spread/slippage/fee/turnover/liquidity capacity
portfolio_exposure_context               # gross/net/sector/single-name exposure state
risk_budget_context                      # limits, drawdown, volatility budget, kill-switch state
point-in-time policy gates
```

Expression-specific costs such as borrow, financing, and option-expression cost may be diagnostics or soft hints only. Layer 5 must not choose or reject a specific expression/instrument.

### 2. Features

`X` is keyed by:

```text
available_time + target_candidate_id + account_or_portfolio_context_ref
```

Core feature blocks:

```text
alpha_confidence_vector
current_position_state
pending_position_state
effective_current_exposure              # current + pending * fill_probability
position_level_friction_context
risk_budget_context
portfolio_exposure_context
policy_gate_context
```

`effective_current_exposure` is a model-local construct used to avoid repeated projection when pending exposure already covers the target. It is not an order instruction.

### 3. Prediction target

Conceptual output:

```text
position_projection_vector
```

Planned physical artifacts:

```text
trading_model.model_06_position_projection
trading_model.model_06_position_projection_explainability
trading_model.model_06_position_projection_diagnostics
```

The primary output keeps the narrow Layer 6-facing target holding-state projection: target position bias, target exposure, current-position alignment, signed position gap, gap magnitude, expected position utility, cost-to-adjust pressure, risk-budget fit, position-state stability, and projection confidence.

Handoff summary fields may expose dominant projection horizon, horizon conflict state, resolved target exposure, resolved position gap, resolution confidence, and reason codes. Diagnostics own raw alpha-to-position priors, effective exposure calculations, and risk/cost reason-code detail.

### 4. Model mapping

V1 mapping should begin as an auditable scaffold:

```text
final adjusted alpha confidence
  -> raw target position prior
  -> effective current exposure calculation
  -> position gap projection
  -> cost-to-adjust and risk-budget evaluation
  -> horizon conflict resolution
  -> position_projection_vector
```

### 5. Loss / error measure

Evaluate wrongness through cost-aware, risk-adjusted position utility, not raw return alone:

- realized position utility by horizon;
- current-position hold utility;
- flat-position utility;
- target-position-vs-current-position lift;
- realized cost to adjust position;
- risk-budget breach and drawdown under projected position;
- regret versus the best candidate exposure in a reviewed exposure grid.

### 6. Training / parameter update

Layer 5 should prefer a candidate-exposure utility curve rather than directly fitting one hindsight-best target exposure:

```text
Q(position_context, candidate_exposure) -> net utility
```

Candidate exposure grids may start with `-1.00, -0.75, -0.50, -0.25, 0.00, +0.25, +0.50, +0.75, +1.00`. All current/pending/cost/risk states must be simulated or recorded point-in-time. Overlapping horizons require purge/embargo.

### 7. Validation / usefulness

Layer 5 must prove incremental value over current-position unchanged, flat-position, Layer 4 alpha-confidence-only exposure mapping, fixed exposure by confidence, cost-blind projection, risk-budget-blind projection, simple horizon averaging, highest-confidence-horizon, and full PositionProjectionModel baselines.

Validation must check utility monotonicity, turnover reduction, cost-pressure usefulness, risk-budget-breach reduction, gap correctness using effective exposure, horizon-resolution value, and no-future-leak evidence.

### 8. Overfitting control

Controls:

- separate inference features from future utility labels;
- avoid learning from strategy-generated historical positions as if they covered all possible exposures;
- train/evaluate candidate exposure utility curves across chronological splits;
- keep expression-specific option-chain features out of Layer 5;
- use bounded normalized exposures and reviewed risk-budget gates;
- require baseline and leakage evidence before promotion.

### 9. Decision deployment

Layer 5 output feeds Layer 6 direct-underlying action planning:

```text
position_projection_vector
  -> UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector
```

It must not output buy/sell/hold/open/close/reverse, choose instruments, read option chains, choose strike/DTE/Greeks, size orders, route orders, or mutate broker/account state.

## Layer 6: UnderlyingActionModel

Status: accepted V1 contract with deterministic scaffold complete for the current model-design phase; production promotion remains evidence-gated.

### 1. Purpose

Layer 6 maps current state, final adjusted alpha confidence, and Layer 5 target holding-state projection into a direct stock/ETF offline action thesis. It answers whether direct underlying expression is eligible, which planned underlying action type applies, how much exposure the offline plan should adjust, and what entry/target/stop/time thesis defines the trade idea.

It outputs `underlying_action_plan` and `underlying_action_vector`; it does not output broker orders, order routing, live execution instructions, or option contracts.

### 2. Inputs

Primary inputs:

```text
alpha_confidence_vector
position_projection_vector
current_underlying_position_state
pending_underlying_order_state
underlying_quote_state
underlying_liquidity_state
underlying_borrow_state
risk_budget_state
policy_gate_state
```

Layer 6 must use effective current underlying exposure:

```text
effective_current_underlying_exposure
= current_underlying_exposure
  + pending_underlying_exposure * pending_fill_probability_estimate
```

### 3. Output contract

The V1 score/vector output exposes these per-horizon score families:

```text
7_underlying_trade_eligibility_score_<horizon>
7_underlying_action_direction_score_<horizon>
7_underlying_trade_intensity_score_<horizon>
7_underlying_entry_quality_score_<horizon>
7_underlying_expected_return_score_<horizon>
7_underlying_adverse_risk_score_<horizon>
7_underlying_reward_risk_score_<horizon>
7_underlying_liquidity_fit_score_<horizon>
7_underlying_holding_time_fit_score_<horizon>
7_underlying_action_confidence_score_<horizon>
```

Resolved plan fields include planned action type, action side, dominant horizon, trade eligibility, trade intensity, entry quality, action confidence, and reason codes.

### 4. Planned action policy

V1 planned action types are `open_long`, `increase_long`, `reduce_long`, `close_long`, `open_short`, `increase_short`, `reduce_short`, `cover_short`, `maintain`, `no_trade`, and `bearish_underlying_path_but_no_short_allowed`.

`maintain` means an existing state remains aligned or adjustment is not worth the cost. `no_trade` means no new direct-underlying operation should be initiated. Opposite-exposure reversal should be represented with conservative reason codes such as `opposite_exposure_detected` and `close_then_reassess_candidate`, not automatic one-step reversal.

### 5. Gate and sizing route

Layer 7 splits hard gates from soft gates. Hard gates include halt, kill switch, risk-budget hard block, liquidity hard fail, trading restriction, direct-short borrow failure, event hard block, and missing required point-in-time state. Soft gates compress action intensity or change entry style.

Planned exposure fields separate target state from current planned action:

```text
target_underlying_exposure_score
current_underlying_exposure_score
pending_adjusted_underlying_exposure_score
effective_current_underlying_exposure_score
underlying_exposure_gap_score
planned_incremental_exposure_score
planned_notional_usd
planned_quantity
```

`planned_quantity` is a pre-execution suggestion, not final order size.

### 6. Entry, price path, and risk plan

Layer 7 emits side-neutral entry and risk fields:

```text
expected_entry_price
worst_acceptable_entry_price
do_not_chase_price
entry_price_limit_direction
expected_target_price
target_price_low
target_price_high
expected_favorable_move_pct
expected_adverse_move_pct
partial_take_profit_price
take_profit_price
stop_loss_price
thesis_invalidation_price
time_stop_minutes
reward_risk_ratio
```

Stop and take-profit prices are thesis fields, not broker stop/limit orders.

### 7. Layer 7 trading-guidance / option-expression handoff

Layer 6 hands Layer 7 an underlying path thesis: direction, expected entry, target/range, stop, holding time, path quality, reversal risk, drawdown risk, favorable/adverse move, and entry assumption. It must not emit option symbol, right, strike, DTE, expiration, delta, Greeks, or specific contract refs.

### 8. Evaluation

Layer 7 labels evaluate plan quality, not raw direction accuracy: target-before-stop, stop-before-target, MFE/MAE, entry fill probability, entry-plan regret, action-type regret, no-trade opportunity cost, bad-trade avoidance, slippage/spread-adjusted return, and realized reward/risk.

### 9. Decision deployment

Layer 6 feeds Layer 7 trading guidance / option expression and execution-side review:

```text
underlying_action_plan
  -> TradingGuidanceModel / OptionExpressionModel
  -> trading_guidance / option_expression_plan / expression_vector
  -> EventRiskGovernor / EventIntelligenceOverlay
  -> trading-execution review and broker-order lifecycle
```

Layer 6 remains offline: no order type, no route, no time-in-force, no send/cancel/replace flag, no broker order id, no broker/account mutation.

## Layer 7: TradingGuidanceModel / OptionExpressionModel

Status: accepted V1 contract with deterministic scaffold complete for the current model-design phase; production promotion remains evidence-gated.

Layer 7 uses Layer 6 underlying path assumptions plus timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, position-projection context, and market-context constraints. It outputs base `trading_guidance` and optional `option_expression_plan` / `expression_vector` rows, and may choose long-call, long-put, or no-option expression plus a point-in-time selected contract reference and constraints.

Layer 7 remains offline: no broker order type, no route, no time-in-force, no send/cancel/replace flag, no broker order id, no final order quantity, and no broker/account mutation. V1 does not construct multi-leg spreads.

## Layer 8: EventRiskGovernor / EventIntelligenceOverlay

Status: accepted V1 event-risk-governor boundary with deterministic scaffold complete for the current model-design phase; production promotion remains evidence-gated.

Contract owner:

```text
docs/09_layer_08_event_risk_governor.md
```

Layer 8 consumes point-in-time event evidence, upstream context refs, and Layer 7 base trading guidance. It outputs `event_risk_intervention` plus event-context/risk evidence that may block new entries, cap exposure, request human review, or nominate reduction/flattening candidates under reviewed policy.

Layer 8 is not a hard upstream alpha input and not a broker/account mutation surface. It must preserve event timing, lifecycle clocks, source priority, canonical-event identity, deduplication status, scope, references, and point-in-time availability, and it must not use post-event outcomes as inference inputs.

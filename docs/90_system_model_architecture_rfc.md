# Direction-Neutral Trading Model Architecture

Status: accepted current route
Owner intent: keep the model stack direct, point-in-time, and current-route authoritative.

## Architecture Summary

```text
point-in-time data foundation
  -> MarketRegimeModel
  -> SectorContextModel
  -> TargetStateVectorModel
     (Layer 3 preprocessing includes anonymous target candidate construction)
  -> Alpha / Confidence Model
  -> Trading Projection Model
  -> OptionExpressionModel
  -> PortfolioRiskModel
  -> unified decision record / downstream execution handoff
```

The stack separates three different questions:

```text
broad market tradability background
  -> market-context-conditioned sector/industry tradability background
  -> anonymous target tradability state
```

This separation is mandatory:

- Layer 1 does not choose sectors, ETFs, stocks, or strategies.
- Layer 2 does not choose final stocks or strategy parameters.
- Layer 3 is the first target-state layer.
- Real ticker/company identity is audit/routing metadata, not a fitting feature.

## Canonical Layers

| Layer | Model class | Stable id | Conceptual output | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | `market_context_state` | Direction-neutral broad market tradability/regime state keyed by `available_time`. |
| 2 | `SectorContextModel` | `sector_context_model` | `sector_context_state` | Direction-neutral sector/industry tradability context under market context. |
| 3 | `TargetStateVectorModel` | `target_state_vector_model` | `target_state_vector` | Direction-neutral market + sector + target state vector for anonymous target candidates; includes candidate construction as preprocessing. |
| 4 | `AlphaConfidenceModel` | `alpha_confidence_model` | `alpha_confidence_state` | Target-state vector to long/short direction confidence, expected value, risk, and uncertainty. |
| 5 | `TradingProjectionModel` | `trading_projection_model` | `trading_projection_state` | Confidence plus position/cost/risk context to offline target action and target exposure. |
| 6 | `OptionExpressionModel` | `option_expression_model` | `expression_state` | Stock/ETF/long-call/long-put expression and option-contract constraints. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | `portfolio_risk_state` | Final offline risk, sizing, exposure, execution-style, exit, and kill-switch gate. |

Do not call Layer 7 `ExecutionModel`; broker mutation and live/paper order placement are outside `trading-model`.

## Model Artifact Rule

Implemented model layers separate the primary output from review and gating surfaces:

```text
model_NN_<layer_slug>
model_NN_<layer_slug>_explainability
model_NN_<layer_slug>_diagnostics
```

The primary output is the narrow downstream dependency contract. Explainability owns human-review internals. Diagnostics owns acceptance, monitoring, and gating evidence. Layer-owned fields use compact `1_*`, `2_*`, ... names in docs, model-facing payloads, and SQL physical columns; SQL writers quote numeric-leading names when needed rather than storing `layer01_*` / `layer02_*` aliases.

`docs/92_vector_taxonomy.md` owns the cross-layer vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing. In particular, `anonymous_target_feature_vector` is a Layer 3 preprocessing/input vector; `target_state_vector` is the Layer 3 model output.

## Point-in-Time Rule

At prediction time `t`, every model may use only data genuinely available before or at `t`.

Timestamp roles:

| Field | Meaning |
|---|---|
| `event_time` | When the underlying event occurred or became scheduled. |
| `available_time` | When the evidence/model output became visible for use. |
| `tradeable_time` | Earliest realistic time the strategy could act on the evidence. |

Backtests must use `available_time` and `tradeable_time`, not hindsight event interpretation.

## Repository Boundary

| Responsibility | Owner |
|---|---|
| Source acquisition and source evidence | `trading-data` |
| Shared registry, global terms, templates, helper policy, control-plane contracts | `trading-manager` |
| Offline model research, model-local validation, model outputs, promotion evidence | `trading-model` |
| Durable storage layout, retention, backup/restore | `trading-storage` |
| Broker/account mutation and live/paper order placement | execution-side repositories |
| Presentation | `trading-dashboard` |

`trading-model` may propose shared contracts, but `trading-manager` owns the registry authority.

## Layer 1: MarketRegimeModel

### Goal

Describe the broad market/cross-asset environment as a point-in-time direction-neutral tradability/regime state. Layer 1 asks whether the market background is clear, stable, low-transition-risk, and able to support downstream trading; it does not decide long/short actions.

Physical output:

```text
trading_model.model_01_market_regime
```

Conceptual downstream output:

```text
market_context_state
```

V2.2 target semantic fields:

```text
available_time
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

The current implementation still carries legacy market-property factor fields until a reviewed migration changes the physical contract. Those fields should be treated as compatibility inputs to the V2.2 semantic split, not as a reason to preserve ambiguous downstream semantics.

### Inputs

Primary feature surface:

```text
trading_data.feature_01_market_regime
```

Eligible evidence includes broad market returns, trend/momentum persistence, volatility, correlation, breadth, concentration, credit/rate/dollar/commodity pressure, funding/liquidity proxies, and market-wide risk-appetite evidence.

### Exclusions

Layer 1 must not use or output:

- sector/industry rankings;
- ETF rankings;
- stock candidates;
- strategy labels;
- option-contract outcomes;
- portfolio PnL;
- future-return labels as construction inputs;
- pre-assigned ETF/sector behavior classes such as `growth`, `defensive`, `cyclical`, `inflation_sensitive`, or `safe_haven`.

ETF/sector behavior attributes belong to Layer 2 as posterior evidence-backed interpretations.

### Method

V1 is simple and auditable:

```text
rolling/expanding scaler
  -> per-signal z-score with reviewed sign direction
  -> factor-level reducer
  -> bounded continuous market-property factors
  -> 1_transition_pressure + 1_data_quality_score
```

No clustering, HMM state, hard state id, or human-readable regime label is required for V1.

### Evidence maturation

Each factor needs a reviewed evidence map:

| Evidence role | Meaning |
|---|---|
| primary evidence | Directly contributes to factor construction. |
| diagnostic evidence | Explains or stress-tests the factor without directly driving it. |
| quality evidence | Supports coverage, freshness, reliability, or `1_data_quality_score`. |
| evaluation-only evidence | Used only after construction to test usefulness. |
| intentionally unused evidence | Excluded with a documented reason. |

### Evaluation

Layer 1 must prove:

- no leakage;
- stable rolling/expanding behavior;
- responsiveness to real market transitions;
- interpretability from supporting evidence;
- explanatory value for Layer 2 sector trend-stability calibration;
- usefulness for option-expression constraints;
- usefulness for portfolio risk, sizing, execution-style, exit, and kill-switch policy;
- no hidden sector/ETF/stock/strategy selection.

## Layer 2: SectorContextModel

### Goal

Infer direction-neutral sector/industry tradability context under broad market context.

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Layer 2 answers:

- Which sector/industry baskets have clean, stable, low-noise, low-transition-risk tradability behavior?
- Under which broad market contexts does each basket trend cleanly, chop, reverse, or cycle?
- Which basket attributes are inferred from evidence rather than pre-labeled?
- Which baskets are eligible, watch-only, or gated out for downstream strategy work?

Layer 2 does **not** choose final stocks.

### Inputs

- `market_context_state` from Layer 1 as conditioning context only.
- `trading_data.feature_02_sector_context` for sector/industry relative strength, trend, volatility, correlation, breadth, and dispersion evidence.
- ETF liquidity, optionability, gap/chop behavior, event density, and abnormal activity evidence.

### Output semantics

Layer 2 primary output is `sector_context_state`, not a pile of peer vectors. Internal/explainability vectors may include observed behavior, attributes, conditional behavior, trend stability, tradability, risk context, and quality diagnostics. The narrow downstream fields separate signed direction, trend quality, stability, transition risk, liquidity tradability, handoff state, handoff bias, and row quality.

### Boundaries

- Do not consume Layer 1 as a sector-ranking scalar.
- Do not consume hard-coded labels such as `technology = growth` or `utilities = defensive`.
- Do not use future returns as production ranking inputs.
- Do not select final stocks in V1.
- Do not use ETF holdings or `stock_etf_exposure` as core Layer 2 behavior-model inputs.
- Output selected/prioritized sector basket handoff state for downstream candidate construction.

### Layer 3 preprocessing: Anonymous Target Candidate Builder

The target candidate builder is part of Layer 3 preprocessing. It is not a separate model, not a separate layer, and not a peer to `TargetStateVectorModel`. It creates anonymous target candidate rows from Layer 2 selected/prioritized sector baskets without exposing ticker identity to model fitting.

The current model-local contract is:

```text
src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md
```

Conceptual model-facing preprocessing fields:

```text
target_candidate_id
anonymous_target_feature_vector
market_context_state_ref
sector_context_state_ref
```

Audit/routing-only metadata:

```text
audit_symbol_ref
routing_symbol_ref
source_sector_or_industry_symbol
source_holding_ref
source_stock_etf_exposure_ref
```

The builder may use ETF holdings and `stock_etf_exposure` to transmit selected sector baskets into stock candidates. Model-facing vectors may include behavior shape, liquidity, volatility, event/risk context, sector context, market context, exposure transmission, and cost/tradability features.

Model-facing vectors must exclude raw ticker/company identity and memorized symbol labels. `target_candidate_id` is a row key only, not a categorical fitting feature.

## Layer 3: TargetStateVectorModel

`TargetStateVectorModel` constructs the target's current direction-neutral tradable state from three inspectable blocks: Layer 1 market state, Layer 2 sector state, and anonymous target-local tape/liquidity/behavior state. It should learn which target board/tape states have stable forward path/tradability relationships after controlling for market and sector context.

It outputs target state vectors, signed current-state direction evidence, direction-neutral tradability scores, cross-state relationship features, state embeddings/clusters, feature-quality diagnostics, and baseline evidence comparing market-only, market+sector, and market+sector+target state vectors. It does not select downstream action variants, output alpha confidence, size positions, or treat positive direction as inherently better than negative direction.

## Layer 4: Alpha / Confidence Model

`AlphaConfidenceModel` consumes `target_state_vector` and estimates long/short direction confidence in `[-1, 1]`, expected value, risk, and uncertainty. It is the first downstream layer allowed to convert direction-neutral state into directional confidence. It does not directly place orders.

## Layer 5: Trading Projection Model

`TradingProjectionModel` consumes confidence, current/pending position state, costs, and risk budget to project an offline target action and target exposure. It owns the mapping from confidence to trade intent, not Layer 3.

## Layer 6: OptionExpressionModel

V1 supports direct stock/ETF comparison plus long call and long put option expressions only.

It consumes option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, alpha/confidence state, trading-projection state, and market context.

It outputs expression choice, contract constraints, no-trade filters, and expected expression quality. Multi-leg structures are deferred.

## Event evidence overlay

The prior architecture reserved an event overlay stage. Under V2.2, event risk remains an overlay used by Layer 3 preprocessing, Alpha/Confidence, Trading Projection, Option Expression, and Portfolio Risk rather than a peer to the three core tradability layers.

Event evidence adjusts earlier layers and final risk based on scheduled events, breaking news, abnormal activity, event memory, earnings concentration, macro windows, and event-driven no-trade states.

It is an overlay/input family, not a separate fourth core tradability layer.

## PortfolioRiskModel

`PortfolioRiskModel` is the final offline risk gate. It uses candidate context, market context, sector context, event overlays, and portfolio state to approve, reject, resize, delay, or alter the trade plan.

It may model execution-style policy, but actual orders remain outside `trading-model`.

## Unified Decision Record

The long-run decision record should reference all layer outputs point-in-time:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_candidate_id
target_state_vector_ref
alpha_confidence_state_ref
trading_projection_state_ref
expression_state_ref
event_evidence_refs
portfolio_risk_state_ref
audit/routing metadata
final offline verdict
```

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

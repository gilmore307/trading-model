# Direction-Neutral Trading Model Architecture

Status: accepted current route; Layers 1-8 model-design phase closed
Owner intent: keep the model stack direct, point-in-time, and current-route authoritative.

## Architecture Summary

```text
point-in-time data foundation
  -> MarketRegimeModel
  -> SectorContextModel
  -> TargetStateVectorModel
     (Layer 3 preprocessing includes anonymous target candidate construction)
  -> EventOverlayModel
  -> AlphaConfidenceModel
  -> PositionProjectionModel
  -> UnderlyingActionModel
  -> OptionExpressionModel
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
| 3 | `TargetStateVectorModel` | `target_state_vector_model` | `target_context_state` | Direction-neutral market + sector + target context for anonymous target candidates; includes candidate construction as preprocessing. |
| 4 | `EventOverlayModel` | `event_overlay_model` | `event_context_vector` | Point-in-time event context, event risk, event direction bias, and event-quality evidence before alpha confidence. |
| 5 | `AlphaConfidenceModel` | `alpha_confidence_model` | `alpha_confidence_vector` | Reviewed state stack plus event correction to adjusted alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal/drawdown risk, and alpha tradability. |
| 6 | `PositionProjectionModel` | `position_projection_model` | `position_projection_vector` | Final adjusted alpha plus current/pending position, cost, and risk context to projected target holding state. |
| 7 | `UnderlyingActionModel` | `underlying_action_model` | `underlying_action_plan` / `underlying_action_vector` | Direct stock/ETF planned action thesis: eligibility, planned action type, planned exposure change, entry/target/stop/time-stop, and Layer 8 underlying-path handoff. |
| 8 | `OptionExpressionModel` | `option_expression_model` | `option_expression_plan` / `expression_vector` | Option-expression selection from Layer 7 underlying thesis and option-chain context; broker mutation remains outside `trading-model`. |

Do not treat Layer 7 or Layer 8 as live execution. Broker mutation and live/paper order placement are outside `trading-model`. There is no accepted Layer 9 inside this repository; post-Layer-8 work crosses into downstream review / execution-owned boundaries.

## Model Artifact Rule

Implemented model layers separate the primary output from review and gating surfaces:

```text
model_NN_<layer_slug>
model_NN_<layer_slug>_explainability
model_NN_<layer_slug>_diagnostics
```

The primary output is the narrow downstream dependency contract. Explainability owns human-review internals. Diagnostics owns acceptance, monitoring, and gating evidence. Layer-owned fields use compact `1_*`, `2_*`, ... names in docs, model-facing payloads, and SQL physical columns; SQL writers quote numeric-leading names when needed rather than storing `layer01_*` / `layer02_*` aliases.

`docs/92_vector_taxonomy.md` owns the cross-layer vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing. In particular, `anonymous_target_feature_vector` is a Layer 3 preprocessing/input vector; `target_context_state` is the Layer 3 conceptual model output.

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

Active semantic fields:

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

Downstream layers should depend on these public state fields rather than implementation-local signal-group names.

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

The Layer 1 generator is simple and auditable:

```text
rolling/expanding scaler
  -> per-signal z-score with reviewed sign direction
  -> internal signal-group reducers
  -> public V2.2 market-context state scores
  -> explainability + diagnostics support artifacts
```

No clustering, HMM state, hard state id, or human-readable regime label is required.

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
- usefulness for position projection, underlying-action thesis, option-expression constraints, and risk-policy handoff;
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

It outputs `target_context_state`: signed current-state direction evidence, direction-neutral tradability scores, cross-state relationship features, optional derived representation diagnostics, feature-quality diagnostics, and baseline evidence comparing market-only, market+sector, and market+sector+target context. It does not select downstream action variants, output alpha confidence, size positions, or treat positive direction as inherently better than negative direction.

## Layer 4: EventOverlayModel

`EventOverlayModel` consumes `market_context_state`, `sector_context_state`, `target_context_state`, and point-in-time `source_04_event_overlay` evidence. It outputs `event_context_vector`: event presence, timing/proximity, intensity, direction bias, uncertainty, gap/reversal/liquidity disruption risk, contagion risk, and event-quality context.

It is now a peer model layer before alpha confidence, not an after-the-fact overlay. It does not output alpha confidence, trading signals, option contracts, or final actions.

Contract owner:

```text
docs/05_layer_04_event_overlay.md
```

## Layer 5: AlphaConfidenceModel

`AlphaConfidenceModel` consumes the reviewed Layer 1/2/3 state stack and uses `event_context_vector` as a correction layer to estimate the final adjusted `alpha_confidence_vector`: alpha direction, alpha strength, expected residual return, confidence, signal reliability, path quality, reversal risk, drawdown risk, and alpha-level tradability. Base/unadjusted alpha from Layer 1/2/3 is retained as diagnostics only; the adjusted vector is the default Layer 6-facing output. It does not project target exposure, choose expression/option contracts, size positions, or place orders.

Contract owner:

```text
docs/06_layer_05_alpha_confidence.md
```

## Layer 6: PositionProjectionModel

`PositionProjectionModel` consumes the final adjusted `alpha_confidence_vector`, current/pending position state, position-level friction, portfolio exposure context, risk-budget context, and point-in-time policy gates to project `position_projection_vector`: target position bias, target exposure, current-position alignment, position gap, expected position utility, cost-to-adjust pressure, risk-budget fit, position-state stability, and projection confidence.

It owns the mapping from alpha confidence to target holding state. It does not output buy/sell/hold/open/close/reverse, choose instruments, read option chains, choose strike/DTE/Greeks, or mutate broker/account state. Contract owner:

```text
docs/07_layer_06_position_projection.md
```

## Layer 7: UnderlyingActionModel

`UnderlyingActionModel` consumes `position_projection_vector`, alpha-confidence refs, current/pending direct-underlying exposure, quote/liquidity state, risk-budget context, and policy gates to produce `underlying_action_plan` and `underlying_action_vector`.

It owns the direct stock/ETF planned action thesis: planned action type, planned exposure change, entry plan, target price/range, stop, thesis invalidation, time-stop, reward/risk, and side-neutral price-path assumptions for Layer 8. Its planned action types are offline plan values such as `open_long`, `increase_long`, `reduce_long`, `close_long`, `open_short`, `increase_short`, `reduce_short`, `cover_short`, `maintain`, and `no_trade`.

It does not emit broker order fields, order type, route, time-in-force, send/cancel/replace instructions, broker order ids, option strike/DTE/delta/Greeks, or account mutations. Contract owner:

```text
docs/08_layer_07_underlying_action.md
```

## Layer 8: OptionExpressionModel

`OptionExpressionModel` consumes Layer 7 underlying price-path assumptions plus timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, event context, and market context to produce `option_expression_plan` and `expression_vector`.

It owns long-call / long-put / no-option-expression selection, selected point-in-time contract references, contract constraints, premium-risk diagnostics, and expression-confidence scores. V1 is single-leg long calls/puts only. Multi-leg structures remain deferred.

It does not emit broker order type, route, time-in-force, final order quantity, send/cancel/replace flags, broker order ids, or account mutation. Contract owner:

```text
docs/09_layer_08_option_expression.md
```

## Unified Decision Record

The long-run decision record should reference all layer outputs point-in-time:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_candidate_id
target_context_state_ref
event_context_vector_ref
alpha_confidence_vector_ref
position_projection_vector_ref
underlying_action_plan_ref
underlying_action_vector_ref
option_expression_plan_ref
expression_vector_ref
audit/routing metadata
offline execution handoff
```

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

# Direction-Neutral Trading Model Architecture
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-15): conceptual Layers 4-8 are now Layer 4 AlphaConfidenceModel, Layer 5 PositionProjectionModel, Layer 6 UnderlyingActionModel, Layer 7 TradingGuidanceModel / OptionExpressionModel, and Layer 8 EventRiskGovernor / EventIntelligenceOverlay. Legacy physical paths such as `model_08_event_risk_governor` and `model_08_option_expression` may remain in implementation notes until a dedicated migration renames them.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: accepted current route; Layers 1-8 model-design phase closed
Owner intent: keep the model stack direct, point-in-time, and current-route authoritative.

## Architecture Summary

```text
point-in-time data foundation
  -> MarketRegimeModel
  -> SectorContextModel
  -> TargetStateVectorModel
     (Layer 3 preprocessing includes anonymous target candidate construction)
  -> EventRiskGovernor
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
| 4 | `AlphaConfidenceModel` | `alpha_confidence_model` | `alpha_confidence_vector` | Reviewed state stack to adjusted alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal/drawdown risk, and alpha tradability. |
| 5 | `PositionProjectionModel` | `position_projection_model` | `position_projection_vector` | Final adjusted alpha plus current/pending position, cost, and risk context to projected target holding state. |
| 6 | `UnderlyingActionModel` | `underlying_action_model` | `underlying_action_plan` / `underlying_action_vector` | Direct stock/ETF planned action thesis: eligibility, planned action type, planned exposure change, entry/target/stop/time-stop, and trading-guidance handoff. |
| 7 | `TradingGuidanceModel` / `OptionExpressionModel` | `trading_guidance_model` / `option_expression_model` | `trading_guidance` / `option_expression_plan` / `expression_vector` | Offline base trading guidance, including optional option-expression selection from the underlying thesis and option-chain context; broker mutation remains outside `trading-model`. |
| 8 | `EventRiskGovernor` / `EventIntelligenceOverlay` | `event_risk_governor` | `event_risk_intervention` / `event_context_vector` | Point-in-time event-risk intervention after base trading guidance; may block/cap/review guidance but must not mutate broker/account state. |

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

## Historical Sampling vs Live Routing

Historical training may use a broader point-in-time sampling universe than live inference routing. Live routing can be narrow because upstream layers gate or prioritize candidates; historical training should not copy those gates when doing so would remove useful contrast.

The canonical policy lives in `docs/97_historical_dataset_scope.md`.

Especially for Layer 3, live routing may send targets from Layer 2 selected/prioritized sector baskets, but historical training may sample targets across other sectors, industries, styles, market caps, and liquidity tiers. Layer 2 context must remain attached to each row as point-in-time context, but it does not have to be a hard historical-training filter.

Promotion evidence should distinguish broad historical generalization from live-route simulation whenever a layer trains on a broader universe than it receives in live routing.

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

The target candidate builder is part of Layer 3 preprocessing. It is not a separate model, not a separate layer, and not a peer to `TargetStateVectorModel`. In live routing, it creates anonymous target candidate rows from Layer 2 selected/prioritized sector baskets without exposing ticker identity to model fitting.

For historical training, the builder may construct broader anonymous target samples across sectors beyond the Layer 2 baskets that would have been selected at that time. Those rows must still carry point-in-time `market_context_state_ref` and `sector_context_state_ref`, remain identity-safe for model fitting, and be evaluated separately for broad generalization versus live-route simulation.

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

## Layer 4: AlphaConfidenceModel

`AlphaConfidenceModel` consumes the reviewed Layer 1/2/3 state stack to estimate the final adjusted `alpha_confidence_vector`: alpha direction, alpha strength, expected residual return, confidence, signal reliability, path quality, reversal risk, drawdown risk, and alpha-level tradability. Base/unadjusted alpha from Layer 1/2/3 is retained as diagnostics only; the adjusted vector is the default Layer 5-facing output. It does not project target exposure, choose expression/option contracts, size positions, or place orders. Event intelligence is no longer a hard upstream prerequisite for this base-alpha layer.

Contract owner:

```text
docs/05_layer_04_alpha_confidence.md
```

## Layer 5: PositionProjectionModel

`PositionProjectionModel` consumes the final adjusted `alpha_confidence_vector`, current/pending position state, position-level friction, portfolio exposure context, risk-budget context, and point-in-time policy gates to project `position_projection_vector`: target position bias, target exposure, current-position alignment, position gap, expected position utility, cost-to-adjust pressure, risk-budget fit, position-state stability, and projection confidence.

It owns the mapping from alpha confidence to target holding state. It does not output buy/sell/hold/open/close/reverse, choose instruments, read option chains, choose strike/DTE/Greeks, or mutate broker/account state. Contract owner:

```text
docs/06_layer_05_position_projection.md
```

## Layer 6: UnderlyingActionModel

`UnderlyingActionModel` consumes `position_projection_vector`, alpha-confidence refs, current/pending direct-underlying exposure, quote/liquidity state, risk-budget context, and policy gates to produce `underlying_action_plan` and `underlying_action_vector`.

It owns the direct stock/ETF planned action thesis: planned action type, planned exposure change, entry plan, target price/range, stop, thesis invalidation, time-stop, reward/risk, and side-neutral price-path assumptions for Layer 7 trading guidance / option expression. Its planned action types are offline plan values such as `open_long`, `increase_long`, `reduce_long`, `close_long`, `open_short`, `increase_short`, `reduce_short`, `cover_short`, `maintain`, and `no_trade`.

It does not emit broker order fields, order type, route, time-in-force, send/cancel/replace instructions, broker order ids, option strike/DTE/delta/Greeks, or account mutations. Contract owner:

```text
docs/07_layer_06_underlying_action.md
```

## Layer 7: TradingGuidanceModel / OptionExpressionModel

`TradingGuidanceModel` / `OptionExpressionModel` consumes Layer 6 underlying price-path assumptions plus timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, and market/position context to produce base offline trading guidance and optional `option_expression_plan` / `expression_vector` rows.

It owns long-call / long-put / no-option-expression selection, selected point-in-time contract references, contract constraints, premium-risk diagnostics, and expression-confidence scores. V1 is single-leg long calls/puts only. Multi-leg structures remain deferred.

It does not emit broker order type, route, time-in-force, final order quantity, send/cancel/replace flags, broker order ids, or account mutation. Contract owner:

```text
docs/08_layer_07_trading_guidance.md
```

## Layer 8: EventRiskGovernor / EventIntelligenceOverlay

`EventRiskGovernor` consumes point-in-time event evidence, upstream context refs, and Layer 7 base trading guidance. It outputs `event_risk_intervention` plus event-context/risk evidence that can block new entries, cap exposure, request human review, or nominate reduction/flattening candidates under reviewed policy.

It is a post-guidance risk-governor boundary, not a hard upstream alpha input and not a broker/account mutation surface. Contract owner:

```text
docs/09_layer_08_event_risk_governor.md
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
alpha_confidence_vector_ref
position_projection_vector_ref
underlying_action_plan_ref
underlying_action_vector_ref
option_expression_plan_ref
expression_vector_ref
event_risk_intervention_ref
event_context_vector_ref
audit/routing metadata
offline execution handoff
```

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

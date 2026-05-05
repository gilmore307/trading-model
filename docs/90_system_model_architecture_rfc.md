# Seven-Layer Trading Model Architecture

Status: accepted current route
Owner intent: keep the model stack direct, point-in-time, and current-route authoritative.

## Architecture Summary

```text
point-in-time data foundation
  -> MarketRegimeModel
  -> SectorContextModel
  -> anonymous target candidate builder + TargetStateVectorModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> EventOverlayModel
  -> PortfolioRiskModel
  -> unified decision record / downstream execution handoff
```

The stack separates three different questions:

```text
broad market background
  -> market-context-conditioned sector/industry background
  -> target-state anonymous target subject
```

This separation is mandatory:

- Layer 1 does not choose sectors, ETFs, stocks, or strategies.
- Layer 2 does not choose final stocks or strategy parameters.
- Layer 3 is the first target-state layer.
- Real ticker/company identity is audit/routing metadata, not a fitting feature.

## Canonical Layers

| Layer | Model class | Stable id | Conceptual output | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | `market_context_state` | Broad market-property state keyed by `available_time`. |
| 2 | `SectorContextModel` | `sector_context_model` | `sector_context_state` | Sector/industry trend-stability and inferred basket attributes under market context. |
| 3 | `TargetStateVectorModel` | `target_state_vector_model` | `target_state_vector` | Market + sector + target state vector for anonymous target candidates. |
| 4 | `TradeQualityModel` | `trade_quality_model` | `trade_quality_state` | Signal quality, outcome distribution, target/stop, MFE/MAE, and holding horizon. |
| 5 | `OptionExpressionModel` | `option_expression_model` | `expression_state` | Stock/ETF/long-call/long-put expression and option-contract constraints. |
| 6 | `EventOverlayModel` | `event_overlay_model` | `event_overlay_state` | Event risk/opportunity adjustments across earlier layers and the risk gate. |
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

Describe the broad market environment as a continuous point-in-time market-property vector.

Physical output:

```text
trading_model.model_01_market_regime
```

Conceptual downstream output:

```text
market_context_state
```

Current fields:

```text
available_time
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

Infer sector/industry basket behavior and trend stability under broad market context.

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Layer 2 answers:

- Which sector/industry baskets have clean and persistent trend behavior?
- Under which broad market contexts does each basket trend cleanly, chop, reverse, or cycle?
- Which basket attributes are inferred from evidence rather than pre-labeled?
- Which baskets are eligible, watch-only, or gated out for downstream strategy work?

Layer 2 does **not** choose final stocks.

### Inputs

- `market_context_state` from Layer 1 as conditioning context only.
- `trading_data.feature_02_sector_context` for sector/industry relative strength, trend, volatility, correlation, breadth, and dispersion evidence.
- ETF liquidity, optionability, gap/chop behavior, event density, and abnormal activity evidence.

### Output blocks

```text
2_sector_observed_behavior_vector
2_sector_attribute_vector
2_sector_conditional_behavior_vector
2_sector_trend_stability_vector
2_sector_tradability_vector
2_sector_risk_context_vector
2_eligibility_state
2_sector_handoff_state
optional 2_sector_selection_parameter
```

### Boundaries

- Do not consume Layer 1 as a sector-ranking scalar.
- Do not consume hard-coded labels such as `technology = growth` or `utilities = defensive`.
- Do not use future returns as production ranking inputs.
- Do not select final stocks in V1.
- Do not use ETF holdings or `stock_etf_exposure` as core Layer 2 behavior-model inputs.
- Output selected/prioritized sector basket handoff state for downstream candidate construction.

## Layer 3 candidate preparation: Anonymous Target Candidate Builder

The target candidate builder is part of Layer 3. It creates anonymous target candidate rows from Layer 2 selected/prioritized sector baskets without exposing ticker identity to model fitting.

The current model-local contract is:

```text
src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md
```

Conceptual fields:

```text
target_candidate_id
anonymous_target_feature_vector
audit_symbol_ref
routing_symbol_ref
market_context_state_ref
sector_context_state_ref
```

The builder may use ETF holdings and `stock_etf_exposure` to transmit selected sector baskets into stock candidates. Model-facing vectors may include behavior shape, liquidity, volatility, event/risk context, sector context, market context, exposure transmission, and cost/tradability features.

Model-facing vectors must exclude raw ticker/company identity and memorized symbol labels. `target_candidate_id` is a row key only, not a categorical fitting feature.

## Layer 3: TargetStateVectorModel

`TargetStateVectorModel` constructs the target's current tradable state from three inspectable blocks: Layer 1 market state, Layer 2 sector state, and anonymous target-local tape/liquidity/behavior state. It should learn which target board/tape states have stable forward trading relationships after controlling for market and sector context.

It outputs target state vectors, cross-state relationship features, state embeddings/clusters, feature-quality diagnostics, and baseline evidence comparing market-only, market+sector, and market+sector+target state vectors. It does not select strategy variants.

## Layer 4: TradeQualityModel

`TradeQualityModel` estimates whether a candidate signal is worth trading. It owns outcome distribution, expected move, target/stop, MFE/MAE, holding horizon, and trade-quality score.

It should model more than direction; it should model payoff shape and adverse/favorable excursion under the selected strategy context.

## Layer 5: OptionExpressionModel

V1 supports direct stock/ETF comparison plus long call and long put option expressions only.

It consumes option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, trade-quality state, and market context.

It outputs expression choice, contract constraints, no-trade filters, and expected expression quality. Multi-leg structures are deferred.

## Layer 6: EventOverlayModel

`EventOverlayModel` adjusts earlier layers and final risk based on scheduled events, breaking news, abnormal activity, event memory, earnings concentration, macro windows, and event-driven no-trade states.

It is an overlay, not merely a final stage.

## Layer 7: PortfolioRiskModel

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
trade_quality_state_ref
expression_state_ref
event_overlay_state_ref
portfolio_risk_state_ref
audit/routing metadata
final offline verdict
```

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

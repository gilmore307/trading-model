# Seven-Layer Trading Model Architecture

Status: accepted current route
Owner intent: keep the model stack direct, point-in-time, and current-route authoritative.

## Architecture Summary

```text
point-in-time data foundation
  -> MarketRegimeModel
  -> SecuritySelectionModel
  -> anonymous target candidate builder + StrategySelectionModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> EventOverlayModel
  -> PortfolioRiskModel
  -> unified decision record / downstream execution handoff
```

The stack separates three different questions:

```text
broad market background
  -> market-conditioned sector/industry background
  -> strategy-aware anonymous target subject
```

This separation is mandatory:

- Layer 1 does not choose sectors, ETFs, stocks, or strategies.
- Layer 2 does not choose final stocks or strategy parameters.
- Layer 3 is the first strategy-aware target layer.
- Real ticker/company identity is audit/routing metadata, not a fitting feature.

## Canonical Layers

| Layer | Model class | Stable id | Conceptual output | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | `market_context_state` | Broad market-property state keyed by `available_time`. |
| 2 | `SecuritySelectionModel` | `security_selection_model` | `sector_context_state` | Sector/industry trend-stability and inferred basket attributes under market context. |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | `strategy_fit_state` | Composite strategy fit for anonymous target candidates. |
| 4 | `TradeQualityModel` | `trade_quality_model` | `trade_quality_state` | Signal quality, outcome distribution, target/stop, MFE/MAE, and holding horizon. |
| 5 | `OptionExpressionModel` | `option_expression_model` | `expression_state` | Stock/ETF/long-call/long-put expression and option-contract constraints. |
| 6 | `EventOverlayModel` | `event_overlay_model` | `event_overlay_state` | Event risk/opportunity adjustments across earlier layers and the risk gate. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | `portfolio_risk_state` | Final offline risk, sizing, exposure, execution-style, exit, and kill-switch gate. |

Do not call Layer 7 `ExecutionModel`; broker mutation and live/paper order placement are outside `trading-model`.

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
  -> transition_pressure + data_quality_score
```

No clustering, HMM state, hard state id, or human-readable regime label is required for V1.

### Evidence maturation

Each factor needs a reviewed evidence map:

| Evidence role | Meaning |
|---|---|
| primary evidence | Directly contributes to factor construction. |
| diagnostic evidence | Explains or stress-tests the factor without directly driving it. |
| quality evidence | Supports coverage, freshness, reliability, or `data_quality_score`. |
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

## Layer 2: SecuritySelectionModel

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
- `trading_data.feature_02_security_selection` for sector/industry relative strength, trend, volatility, correlation, breadth, and dispersion evidence.
- ETF holdings snapshots for eligible sector/industry equity ETFs.
- `stock_etf_exposure` as source-backed composition/transmission evidence.
- ETF liquidity, optionability, gap/chop behavior, event density, and abnormal activity evidence.

### Output blocks

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

### Boundaries

- Do not consume Layer 1 as a sector-ranking scalar.
- Do not consume hard-coded labels such as `technology = growth` or `utilities = defensive`.
- Do not use future returns as production ranking inputs.
- Do not select final stocks in V1.
- Use ETF holdings and `stock_etf_exposure` for composition diagnostics and downstream handoff references.

## Anonymous Target Candidate Builder

The target candidate builder creates strategy-aware candidate rows for Layer 3+ without exposing ticker identity to model fitting.

Conceptual fields:

```text
target_candidate_id
anonymous_target_feature_vector
audit_symbol_ref
routing_symbol_ref
market_context_state_ref
sector_context_state_ref
```

Model-facing vectors may include behavior shape, liquidity, volatility, event/risk context, sector context, market context, and cost/tradability features.

Model-facing vectors must exclude raw ticker/company identity and memorized symbol labels.

## Layer 3: StrategySelectionModel

`StrategySelectionModel` composes and weights strategy components for anonymous target candidates. It should compare strategy fit under market/sector/target context rather than choosing one historical champion variant.

It outputs strategy availability, strategy fit, component weights, parameter neighborhoods, disabled-strategy reasons, and robustness evidence.

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
strategy_fit_state_ref
trade_quality_state_ref
expression_state_ref
event_overlay_state_ref
portfolio_risk_state_ref
audit/routing metadata
final offline verdict
```

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

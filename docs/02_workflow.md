# Workflow

## Purpose

This file defines the intended offline modeling workflow for `trading-model`.

## Primary Flow

```text
point-in-time data artifacts
  -> feature/label builders
  -> MarketRegimeModel
  -> SecuritySelectionModel (market-state-conditioned sector trend stability)
  -> anonymized target candidate builder
  -> StrategySelectionModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> EventOverlayModel adjustments
  -> PortfolioRiskModel
  -> unified decision record + validation evidence
```

`EventOverlayModel` is an overlay, not merely a late stage. It can modify regime transition risk, candidate selection, strategy availability, signal scores, option structure constraints, or risk-gate reductions.

`PortfolioRiskModel` is the final offline execution-gate model. It may approve, reject, resize, delay, or alter candidate trades, but actual order placement remains outside this repository.

## Operating Principles

- Every model layer should be decomposed with the standard nine-part structure in `docs/08_model_decomposition.md`: data, features, prediction target, model mapping, loss/error measure, training/update process, validation/usefulness, overfitting control, and decision deployment.
- Every workflow must be point-in-time: no future data, no full-history fitting for historical predictions, no post-event explanation leakage.
- Keep broad market background, sector/industry trend-stability background, and target subject selection separate. Layer 1 describes the broad environment; Layer 2 identifies which sector/industry baskets have stable, tradable trends under each market environment; target/security choice must be strategy-aware, anonymized for model fitting, and belongs downstream.
- `MarketRegimeModel` must be market/data-feature based and limited to broad state description. It is background context for option-expression choice, strategy compatibility, and risk/execution policy; it must not rank ETFs, sectors, or stocks, and must not pre-label ETF/sector attributes as growth, defensive, cyclical, safe-haven, or similar behavior classes.
- `SecuritySelectionModel` should select and score tradable sector/industry baskets by studying trend stability under different broad market states: persistent one-way trends, clean breakdowns, or repeatable cycles rather than random chop. It owns ETF/sector attribute discovery from evidence rather than consuming pre-assigned behavior labels from Layer 1. ETF holdings/exposure are composition diagnostics. It should not select final stocks before `StrategySelectionModel` chooses a compatible strategy.
- `StrategySelectionModel` should compose a comprehensive strategy from multiple strategy components/families using walk-forward or similarly time-safe evidence, not historical champion-picking of one isolated variant. It is the first layer where target/security refinement can become meaningful because the target is evaluated together with the strategy. Target candidates should be anonymized for model fitting so the unsupervised strategy model learns tradable shapes and context fit, not ticker identity.
- `TradeQualityModel` should model outcome distribution and risk, not only direction.
- `OptionExpressionModel` V1 is limited to single-leg long call / long put option expressions and must use timestamped option-chain snapshots, bid/ask, liquidity, IV/Greeks, conservative fills, and failure-to-fill assumptions. It should consume market-state context for contract-expression constraints such as DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade filters.
- `EventOverlayModel` must preserve event/evidence timing and source priority.
- `PortfolioRiskModel` must account for portfolio exposure, correlation, drawdown state, liquidity, slippage, kill-switch behavior, and market-state-conditioned execution/risk policy.
- Research outputs need manifests and ready signals before downstream promotion.
- Shared fields, statuses, type values, helpers, and reusable templates must come from `trading-manager`.
- Runtime outputs must be written outside Git-tracked source paths.
- Cross-repository handoffs should use accepted request, artifact, manifest, and ready-signal contracts.

## Phased Build Order

### Phase 1: MarketRegimeModel

Deliver market-state feature contracts, rolling/expanding state-vector prototype, transition pressure, and evidence that the state vector is stable, interpretable, and useful as background context for option expression, strategy compatibility, and risk/execution policy without ETF/security selection leakage.

### Phase 2: SecuritySelectionModel

Deliver sector/industry rotation research, market-state-conditioned sector trend-stability profiles, sector/industry ETF holdings composition/exposure diagnostics, `stock_etf_exposure` derived table proposal, sector/industry basket parameter rows, eligibility/gating rules, optionability/liquidity filters, and downstream handoff references. Do not derive sector ranking from a Layer 1 market-state scalar, and do not select final stocks in Layer 2 V1.

### Phase 3: StrategySelectionModel

Deliver a small strategy-family library, limited variants, composite-strategy weighting rules, anonymized target-candidate feature contracts, candidate/market/sector-context-conditioned performance tables, disabled-strategy rules, and parameter-neighborhood stability evidence.

### Phase 4: TradeQualityModel

Deliver underlying-only trade labels, triple-barrier labeling, trade-quality score, expected return/target/stop/holding-time outputs, and score-decile performance evidence.

### Phase 5: OptionExpressionModel

Deliver option-chain snapshot feature contract, long call/put ranker only, market-state-conditioned DTE/delta/moneyness/IV constraints, liquidity/IV/crush filters, expected option PnL, and conservative fill/slippage assumptions. Multi-leg spreads are deferred.

### Phase 6: EventOverlayModel

Deliver scheduled event risk score, earnings IV-crush model, macro event risk model, abnormal option/price/volume activity detector, stock/equity abnormal activity detector, and overlay adjustment rules for the other layers.

### Phase 7: PortfolioRiskModel

Deliver position sizing research, exposure monitor, market-state-conditioned order/execution rules, exit lifecycle rules, kill-switch logic, and PnL/attribution dashboard contract.

## Unified Decision Record

Every candidate trade should ultimately produce a point-in-time decision record containing all seven layer outputs. The decision record is the audit/replay/retraining spine.

The canonical draft shape lives in `docs/07_system_model_architecture_rfc.md` until promoted through `trading-manager` registry/contracts.

## Collaboration Boundary

`trading-model` collaborates with other trading repositories through explicit contracts, not direct mutation of their local state.

Upstream inputs and downstream outputs should be described by artifact references, manifests, ready signals, requests, or accepted storage contracts.

## Open Gaps

- Exact first implementation slice under the new seven-layer scope.
- Exact request shape consumed or produced by this repository.
- Exact artifact, manifest, and ready-signal schema interactions.
- Exact shared storage paths and references.
- Exact test harness and fixture policy.
- Exact package/source layout once implementation begins.
- Whether `trading-strategy` remains separate or strategy-selection research becomes model-local until later split.

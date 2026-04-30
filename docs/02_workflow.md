# Workflow

## Purpose

This file defines the intended offline modeling workflow for `trading-model`.

## Primary Flow

```text
point-in-time data artifacts
  -> feature/label builders
  -> MarketRegimeModel
  -> SecuritySelectionModel
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

- Every workflow must be point-in-time: no future data, no full-history fitting for historical predictions, no post-event explanation leakage.
- `MarketRegimeModel` must be market/data-feature based and limited to state description; strategy outcomes, ETF rankings, and security selection labels are attached only after state construction for downstream evaluation.
- `SecuritySelectionModel` first derives base and sector-weighted market-context parameters from the Layer 1 vector, then builds tradable sector/industry ETF and stock candidate pools from those market parameters, sector/industry ETF holdings exposure, full-market scans, trend clarity, trend persistence, certainty, liquidity, optionability, and event exclusions; it does not choose entry timing or simply chase highest return.
- `StrategySelectionModel` must use walk-forward or similarly time-safe evaluation, not historical champion-picking.
- `TradeQualityModel` should model outcome distribution and risk, not only direction.
- `OptionExpressionModel` V1 is limited to single-leg long call / long put option expressions and must use timestamped option-chain snapshots, bid/ask, liquidity, IV/Greeks, conservative fills, and failure-to-fill assumptions.
- `EventOverlayModel` must preserve event/evidence timing and source priority.
- `PortfolioRiskModel` must account for portfolio exposure, correlation, drawdown state, liquidity, slippage, and kill-switch behavior.
- Research outputs need manifests and ready signals before downstream promotion.
- Shared fields, statuses, type values, helpers, and reusable templates must come from `trading-manager`.
- Runtime outputs must be written outside Git-tracked source paths.
- Cross-repository handoffs should use accepted request, artifact, manifest, and ready-signal contracts.

## Phased Build Order

### Phase 1: MarketRegimeModel

Deliver market-state feature contracts, rolling/expanding state-vector prototype, transition pressure, and evidence that the state vector is stable, interpretable, and useful without ETF/security selection leakage.

### Phase 2: SecuritySelectionModel

Deliver base/sector-weighted market-context parameter design, sector/industry ETF holdings exposure matrix, `stock_etf_exposure` derived table proposal, sector/industry ETF and stock trend-clarity/certainty scoring, full-market scan candidate logic, long/short/watch/excluded candidate pools, optionability/liquidity filters, and sector/style transmission evidence.

### Phase 3: StrategySelectionModel

Deliver a small strategy-family library, limited variants, regime/security-conditioned performance tables, disabled-strategy rules, and parameter-neighborhood stability evidence.

### Phase 4: TradeQualityModel

Deliver underlying-only trade labels, triple-barrier labeling, trade-quality score, expected return/target/stop/holding-time outputs, and score-decile performance evidence.

### Phase 5: OptionExpressionModel

Deliver option-chain snapshot feature contract, long call/put ranker only, liquidity/IV/crush filters, expected option PnL, and conservative fill/slippage assumptions. Multi-leg spreads are deferred.

### Phase 6: EventOverlayModel

Deliver scheduled event risk score, earnings IV-crush model, macro event risk model, abnormal option/price/volume activity detector, stock/equity abnormal activity detector, and overlay adjustment rules for the other layers.

### Phase 7: PortfolioRiskModel

Deliver position sizing research, exposure monitor, order/execution rules, exit lifecycle rules, kill-switch logic, and PnL/attribution dashboard contract.

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

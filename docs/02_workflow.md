# Workflow

## Purpose

This file defines the intended offline modeling workflow for `trading-model`.

## Primary Flow

```text
point-in-time data artifacts
  -> feature/label builders
  -> MarketRegimeModel
  -> StrategySelectionModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> EventOverlayModel adjustments
  -> PortfolioRiskModel
  -> unified decision record + validation evidence
```

Layer 5 is an overlay, not merely a late stage. It can modify regime transition risk, disable strategies, change signal scores, alter option structure constraints, or force risk-gate reductions.

Layer 6 is the final offline execution-gate model. It may approve, reject, resize, delay, or alter candidate trades, but actual order placement remains outside this repository.

## Operating Principles

- Every workflow must be point-in-time: no future data, no full-history fitting for historical predictions, no post-event explanation leakage.
- `MarketRegimeModel` must be market/data-feature based; strategy outcomes are attached after state construction for evaluation.
- `StrategySelectionModel` must use walk-forward or similarly time-safe evaluation, not historical champion-picking.
- `TradeQualityModel` should model outcome distribution and risk, not only direction.
- `OptionExpressionModel` must use timestamped option-chain snapshots, bid/ask, liquidity, IV/Greeks, conservative fills, and failure-to-fill assumptions.
- `EventOverlayModel` must preserve event/evidence timing and source priority.
- `PortfolioRiskModel` must account for portfolio exposure, correlation, drawdown state, liquidity, slippage, and kill-switch behavior.
- Research outputs need manifests and ready signals before downstream promotion.
- Shared fields, statuses, type values, helpers, and reusable templates must come from `trading-main`.
- Runtime outputs must be written outside Git-tracked source paths.
- Cross-repository handoffs should use accepted request, artifact, manifest, and ready-signal contracts.

## Phased Build Order

### Phase 1: Data foundation + Layer 1

Deliver market-state feature contracts, rolling/expanding regime model prototype, regime probabilities, transition risk, and evidence that regimes are stable, interpretable, and useful.

### Phase 2: Layer 2 strategy library

Deliver a small strategy-family library, limited variants, regime-conditioned performance tables, disabled-strategy rules, and parameter-neighborhood stability evidence.

### Phase 3: Layer 3 signal-quality model

Deliver underlying-only trade labels, triple-barrier labeling, trade-quality score, expected return/target/stop/holding-time outputs, and score-decile performance evidence.

### Phase 4: Layer 4 option selector

Deliver option-chain snapshot feature contract, long call/put and debit-spread ranker, liquidity/IV/crush filters, expected option PnL, and conservative fill/slippage assumptions.

### Phase 5: Layer 5 event overlay

Deliver scheduled event risk score, earnings IV-crush model, macro event risk model, abnormal price/volume/option activity detector, and overlay adjustment rules for the other layers.

### Phase 6: Layer 6 risk/execution gate

Deliver position sizing research, exposure monitor, order/execution rules, exit lifecycle rules, kill-switch logic, and PnL/attribution dashboard contract.

## Unified Decision Record

Every candidate trade should ultimately produce a point-in-time decision record containing all six layer outputs. The decision record is the audit/replay/retraining spine.

The canonical draft shape lives in `docs/07_system_model_architecture_rfc.md` until promoted through `trading-main` registry/contracts.

## Collaboration Boundary

`trading-model` collaborates with other trading repositories through explicit contracts, not direct mutation of their local state.

Upstream inputs and downstream outputs should be described by artifact references, manifests, ready signals, requests, or accepted storage contracts.

## Open Gaps

- Exact first implementation slice under the new six-layer scope.
- Exact request shape consumed or produced by this repository.
- Exact artifact, manifest, and ready-signal schema interactions.
- Exact shared storage paths and references.
- Exact test harness and fixture policy.
- Exact package/source layout once implementation begins.
- Whether `trading-strategy` remains separate or strategy-selection research becomes model-local until later split.

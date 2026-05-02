# Workflow

## Purpose

This file defines the current offline modeling workflow for `trading-model`.

## Primary Flow

```text
point-in-time data artifacts
  -> MarketRegimeModel
  -> SecuritySelectionModel
  -> anonymous target candidate builder
  -> StrategySelectionModel
  -> TradeQualityModel
  -> OptionExpressionModel
  -> EventOverlayModel
  -> PortfolioRiskModel
  -> unified decision record + validation evidence
```

`EventOverlayModel` is an overlay. It can adjust earlier layer outputs and the final risk gate.

`PortfolioRiskModel` is the final offline risk gate. It may approve, reject, resize, delay, or alter a candidate trade plan, but actual order placement remains outside this repository.

## Operating Principles

- Every layer uses the nine-part design structure in `docs/08_model_decomposition.md`.
- Every workflow is point-in-time: no future data, no full-history fitting for historical predictions, and no post-event explanation leakage.
- Keep three contexts separate:
  - Layer 1: broad market background;
  - Layer 2: market-context-conditioned sector/industry background;
  - Layer 3+: strategy-aware anonymous target work.
- Layer 1 must not rank ETFs, sectors, or stocks and must not pre-label ETF/sector behavior classes.
- Layer 2 infers ETF/sector attributes from evidence and studies trend stability under market context. It does not choose final stocks in V1.
- Target/security choice becomes meaningful only after strategy context is introduced. Model-facing target vectors must anonymize ticker/company identity.
- `TradeQualityModel` models payoff quality and outcome distribution, not only direction.
- `OptionExpressionModel` V1 supports direct stock/ETF comparison plus long call / long put only.
- `EventOverlayModel` preserves event timing and source priority.
- `PortfolioRiskModel` accounts for exposure, correlation, drawdown state, liquidity, slippage, kill-switch behavior, and market-context-conditioned execution/risk policy.
- Research outputs need manifests and ready signals before downstream promotion.
- Shared fields, statuses, type values, helpers, templates, and reusable contracts must come from `trading-manager`.
- Runtime outputs must be written outside Git-tracked source paths.

## Phased Build Order

### Phase 1: MarketRegimeModel

Deliver `model_01_market_regime` as a point-in-time continuous market-property vector and evaluate `market_context_state` for stability, interpretability, Layer 2 explanatory value, option-expression usefulness, and portfolio-risk usefulness.

### Phase 2: SecuritySelectionModel

Deliver `sector_context_state` for eligible sector/industry baskets: inferred attributes, conditional behavior profiles, trend-stability vectors, composition diagnostics, tradability diagnostics, risk context, eligibility, and downstream handoff references.

### Phase 3: Anonymous target candidate builder + StrategySelectionModel

Deliver anonymous target candidate rows, strategy-family/component library, composite strategy weighting, disabled-strategy rules, parameter-neighborhood stability, and target/market/sector-context-conditioned performance evidence.

### Phase 4: TradeQualityModel

Deliver trade-quality labels, score, outcome distribution, target/stop, MFE/MAE, holding-period outputs, and score-decile evidence.

### Phase 5: OptionExpressionModel

Deliver option-chain snapshot features, direct/long-call/long-put expression ranker, market-context-conditioned contract constraints, liquidity/IV/crush filters, expected option PnL, and conservative fill/slippage assumptions.

### Phase 6: EventOverlayModel

Deliver scheduled-event risk, earnings/event impact models, abnormal option/price/volume activity detection, and overlay adjustment rules.

### Phase 7: PortfolioRiskModel

Deliver position sizing, exposure monitoring, market-context-conditioned execution policy, exit lifecycle, kill-switch logic, and attribution evidence.

## Unified Decision Record

Every candidate trade should ultimately produce a point-in-time decision record containing references to all accepted layer outputs.

The exact shared record contract must be promoted through `trading-manager` before cross-repository dependence.

## Collaboration Boundary

`trading-model` collaborates through explicit contracts: artifact references, manifests, ready signals, requests, and accepted storage contracts. It does not mutate other repositories' local state directly.

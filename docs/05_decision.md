# Decision


## D001 - Market-state discovery is market-only

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State discovery inputs must be market/data-source features only; strategy performance is excluded until after state tables exist.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D002 - Model research is offline

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

This repository produces research artifacts and verdicts, not live trading decisions or order placement.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D003 - Generated model artifacts stay out of Git

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State tables, trained outputs, model artifacts, and research runs are runtime artifacts unless accepted as tiny fixtures.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.

## D004 - Six-layer offline modeling architecture supersedes market-state-only repository purpose

Date: 2026-04-27

### Context

The trading system data-source layer is now considered sufficiently complete for v1, and the next phase is to clarify model requirements. The prior `trading-model` boundary treated the repository primarily as market-state/regime research. Chentong explicitly replaced that old intent and accepted the current six-layer architecture as the new basis.

### Decision

`trading-model` is the offline modeling home for the six-layer trading decision system:

1. `MarketRegimeModel` (`market_regime_model`);
2. `StrategySelectionModel` (`strategy_selection_model`);
3. `TradeQualityModel` (`trade_quality_model`);
4. `OptionExpressionModel` (`option_expression_model`);
5. `EventOverlayModel` (`event_overlay_model`);
6. `PortfolioRiskModel` (`portfolio_risk_model`).

Layer 5 is an overlay that can affect all earlier layers and the risk gate. Layer 6 is the final offline risk/execution gate, but live order placement remains outside this repository.

### Rationale

The model requirements determine cleaning, feature shape, event projection, bundle composition, and decision records. Keeping the full modeling stack in view prevents the data layer from hardening premature schemas and prevents Layer 1 from being designed as an isolated regime-labeling exercise.

### Consequences

- Earlier market-state-only wording is superseded except for the still-valid principle that Layer 1 regime discovery itself must not use strategy performance as an input.
- Phase 1 should still start with point-in-time market-state/regime modeling, but as Layer 1 of the full stack.
- Layers 2-6 may be implemented in phases inside `trading-model` unless a later decision splits ownership.
- Raw acquisition remains in `trading-data`; global shared contracts still route through `trading-main`; live/paper order placement remains outside `trading-model`.
- All layers must obey point-in-time validation and avoid event/news/label leakage.

## D005 - Canonical six-layer model names

Date: 2026-04-27

### Context

After accepting the six-layer architecture, the model layers need stable names before data organization, schemas, decision records, code packages, and registry proposals are finalized.

### Decision

Use the following canonical model names and stable ids:

| Layer | Model class | Stable id | Chinese name |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 |
| 2 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 |
| 3 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 |
| 4 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 |
| 5 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 |
| 6 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 |

Layer 5 remains an overlay. Layer 6 may model execution-gate logic, but it must not be called `ExecutionModel` because live/paper order placement is outside `trading-model`.

### Rationale

Stable names prevent schema drift and keep future data organization, decision records, artifacts, code modules, and registry rows aligned.

### Consequences

- Docs, code, artifact metadata, and registry proposals should use these names unless a later decision renames them.
- Machine-facing paths/configs should prefer the stable ids.
- The canonical naming table in `docs/07_system_model_architecture_rfc.md` is the working reference until promoted into `trading-main` registry/contracts.

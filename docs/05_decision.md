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

## D004 - Seven-layer offline modeling architecture supersedes market-state-only repository purpose

Date: 2026-04-27

### Context

The trading system data-source layer is now considered sufficiently complete for v1, and the next phase is to clarify model requirements. The prior `trading-model` boundary treated the repository primarily as market-state/regime research. Chentong explicitly replaced that old intent and accepted the current seven-layer architecture as the new basis.

### Decision

`trading-model` is the offline modeling home for the seven-layer trading decision system:

1. `MarketRegimeModel` (`market_regime_model`);
2. `SecuritySelectionModel` (`security_selection_model`);
3. `StrategySelectionModel` (`strategy_selection_model`);
4. `TradeQualityModel` (`trade_quality_model`);
5. `OptionExpressionModel` (`option_expression_model`);
6. `EventOverlayModel` (`event_overlay_model`);
7. `PortfolioRiskModel` (`portfolio_risk_model`).

Layer 6 is an overlay that can affect all earlier layers and the risk gate. Layer 7 is the final offline risk/execution gate, but live order placement remains outside this repository.

### Rationale

The model requirements determine cleaning, feature shape, event projection, bundle composition, and decision records. Keeping the full modeling stack in view prevents the data layer from hardening premature schemas and prevents Layer 1 from being designed as an isolated regime-labeling exercise.

### Consequences

- Earlier market-state-only wording is superseded except for the still-valid principle that Layer 1 regime discovery itself must not use strategy performance as an input.
- Phase 1 should still start with point-in-time market-state/regime modeling, but as Layer 1 of the full stack.
- Layers 2-7 may be implemented in phases inside `trading-model` unless a later decision splits ownership.
- Raw acquisition remains in `trading-data`; global shared contracts still route through `trading-main`; live/paper order placement remains outside `trading-model`.
- All layers must obey point-in-time validation and avoid event/news/label leakage.

## D005 - Canonical seven-layer model names

Date: 2026-04-27

### Context

After accepting the seven-layer architecture, the model layers need stable names before data organization, schemas, decision records, code packages, and registry proposals are finalized.

### Decision

Use the following canonical model names and stable ids:

| Layer | Model class | Stable id | Chinese name |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 |
| 2 | `SecuritySelectionModel` | `security_selection_model` | 标的选择模型 |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 |
| 4 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 |
| 5 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 |
| 6 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 |

Layer 6 remains an overlay. Layer 7 may model execution-gate logic, but it must not be called `ExecutionModel` because live/paper order placement is outside `trading-model`.

### Rationale

Stable names prevent schema drift and keep future data organization, decision records, artifacts, code modules, and registry rows aligned.

### Consequences

- Docs, code, artifact metadata, and registry proposals should use these names unless a later decision renames them.
- Machine-facing paths/configs should prefer the stable ids.
- The canonical naming table in `docs/07_system_model_architecture_rfc.md` is the working reference until promoted into `trading-main` registry/contracts.

## D006 - SecuritySelectionModel bridges market regime to tradable symbols

Date: 2026-04-28

### Context

ETF holdings are not primarily a `MarketRegimeModel` input. Their key role is to transmit sector/style strength from ETF baskets into individual tradable stock candidates. The prior architecture jumped from market regime directly to strategy selection, which skipped the question of which symbols deserve strategy evaluation under the current regime.

### Decision

Add `SecuritySelectionModel` (`security_selection_model`) as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.

`SecuritySelectionModel` owns target/security selection and universe construction. It uses market/sector/style context, ETF holdings exposures, full-market scans, individual stock relative strength, liquidity, optionability, and event exclusions to produce long, short, watch, and excluded candidate pools.

### Rationale

Different market regimes require different selection styles. Risk-on regimes may prefer high-relative-strength core holdings of strong ETFs; risk-off regimes may prefer defensive/low-volatility names or ETFs; rotation regimes may prefer newly strengthening holdings or laggards catching up. This is a distinct modeling problem from choosing strategy family or signal entry quality.

### Consequences

- `MarketRegimeModel` should output sector/style scores useful for security selection.
- `etf_holding_snapshot` becomes an important upstream data kind for Layer 2.
- A derived point-in-time `stock_etf_exposure` table should be designed, either model-local first or registered through `trading-main` if cross-repository use is needed.
- `StrategySelectionModel` consumes selected candidate pools instead of scanning the whole universe directly.
- Event and optionability exclusions can remove symbols before strategy evaluation.

## D007 - OptionExpressionModel V1 is single-leg long options only

Date: 2026-04-28

### Context

`OptionExpressionModel` selects the option contract or expression after signal quality and expected underlying move are known. Multi-leg structures introduce materially more complexity in pricing, margin, fill simulation, slippage, exit management, and risk controls.

### Decision

V1 `OptionExpressionModel` supports only simple single-leg option expressions:

- long call;
- long put.

Stock/ETF direct expression may remain a comparison or fallback, but V1 option expression must not choose debit spreads, calendars, diagonals, straddles, strangles, condors, butterflies, ratio spreads, or naked short options.

### Rationale

Single-leg long options are sufficient for the first option-expression research slice and keep modeling, backtesting, and execution assumptions auditable. Multi-leg option structures should wait until option-chain snapshot quality, conservative fill logic, slippage modeling, and exit lifecycle handling are proven.

### Consequences

- `OptionExpressionModel` V1 scoring ranks eligible calls/puts, not combinations of legs.
- Required inputs remain option chain snapshot, bid/ask, volume/open interest, DTE, IV, Greeks, liquidity, and previous model outputs.
- Multi-leg structures are explicitly deferred and should not appear in V1 decision records except as rejected/deferred capabilities.

## D008 - MarketRegimeModel V1 outputs a continuous market-state vector

Date: 2026-04-29
Status: Accepted

### Context

Layer 1 initially discussed unsupervised clustering, state ids, state probabilities, and human-readable regime names. Chentong clarified that hard states are unlikely to directly help later security selection or strategy selection because they are coarse, unstable after refits, and require another lookup layer to recover the underlying market conditions.

The useful downstream information is the concrete market-condition vector: trend, volatility stress, correlation stress, credit/rate/dollar/commodity pressure, sector rotation, breadth, risk appetite, and transition pressure.

### Decision

`MarketRegimeModel` V1 should not require clustering, HMM state assignment, hard `state_id`, `state_probability_*`, or pre-assigned human-readable labels.

The primary V1 output is a continuous point-in-time market-state vector in `trading_model.model_01_market_regime`, keyed by `available_time`.

The model should remain unsupervised in the sense that it does not train on pre-assigned market labels. It may use rolling/expanding standardization and feature-block factor/score extraction from `trading_derived.derived_01_market_regime`.

### Consequences

- Discrete state/cluster artifacts are deferred and optional research diagnostics, not the main downstream contract.
- Layer 2/3 should consume continuous market-condition factors/scores rather than hard regime labels.
- Future-return labels may be used for evaluation only, not for constructing Layer 1 model outputs.
- The first implementation slice should focus on stable, interpretable, point-in-time factor/score generation before adding clustering or visualization branches.

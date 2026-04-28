# trading-model

`trading-model` is the offline modeling repository for the seven-layer trading decision system.

It owns point-in-time model research, validation, decision-record prototypes, and model outputs for:

1. MarketRegimeModel (`market_regime_model`);
2. SecuritySelectionModel (`security_selection_model`);
3. StrategySelectionModel (`strategy_selection_model`);
4. TradeQualityModel (`trade_quality_model`);
5. OptionExpressionModel (`option_expression_model`);
6. EventOverlayModel (`event_overlay_model`);
7. PortfolioRiskModel (`portfolio_risk_model`).

It does not own raw source acquisition, live/paper order placement, broker/account mutation, global registry authority, generated runtime artifacts committed to Git, or secrets.

## Top-Level Structure

```text
docs/        Repository scope, context, workflow, acceptance, task, decisions, memory, and architecture RFCs.
```

Source, scripts, tests, and package layout are intentionally not created yet. Add them only after the first implementation slice, storage expectations, fixture policy, and cross-repository contracts are explicit. When implementation begins, use `src/` for importable/reusable code, `scripts/` for executable maintenance or operational entrypoints, and `tests/` for first-party tests; `scripts/` may import `src/`, but `src/` must not import `scripts/`.

## Docs Spine

```text
docs/
  00_scope.md
  01_context.md
  02_workflow.md
  03_acceptance.md
  04_task.md
  05_decision.md
  06_memory.md
  07_system_model_architecture_rfc.md
```

## Platform Dependencies

- `trading-main` owns global contracts, registry, shared helpers, templates, and platform guidance.
- `trading-data` owns raw acquisition and source-evidence bundles.
- `trading-storage` owns durable storage layout and retention unless this repository is proposing a reviewed storage contract.
- `trading-manager` owns orchestration and lifecycle routing.
- Execution-side repositories own broker/account mutation.

Any new global helper, reusable template, shared field, status, type, config key, or vocabulary discovered here must be routed back to `trading-main` before other repositories depend on it.

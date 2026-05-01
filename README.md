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
src/         Importable model-output, model-governance, promotion, and evaluation implementation code.
scripts/     SQL generation wrappers and operational entrypoints.
tests/       First-party unit tests using in-memory fixtures/fake cursors.
```

Current implementation packages:

```text
src/model_outputs/model_01_market_regime/
src/model_governance/
src/model_evaluation/
```

Current runtime wrappers:

```text
scripts/generate_model_01_market_regime.py
scripts/ensure_model_governance_schema.py
scripts/evaluate_model_01_market_regime.py
scripts/clear_model_development_database.py
scripts/run_market_regime_development_smoke.py
scripts/review_market_regime_promotion.py
```

`src/` owns reusable model logic. `scripts/` may import `src/`; `src/` must not import `scripts/`.

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
  08_model_decomposition.md
```

`docs/08_model_decomposition.md` is the model-design review template: each layer should be decomposed by data, features, target, model mapping, loss, training/update process, validation, overfitting control, and decision deployment before implementation or promotion expands.

## Platform Dependencies

- `trading-manager` owns global contracts, registry, shared helpers, templates, and platform guidance.
- `trading-data` owns raw acquisition and source-evidence bundles.
- `trading-storage` owns durable storage layout and retention unless this repository is proposing a reviewed storage contract.
- `trading-manager` owns control-plane orchestration and lifecycle routing.
- Execution-side repositories own broker/account mutation.

Any new global helper, reusable template, shared field, status, type, config key, or vocabulary discovered here must be routed back to `trading-manager` before other repositories depend on it.

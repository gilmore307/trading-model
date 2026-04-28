# trading-model

`trading-model` is the offline modeling repository for the six-layer trading decision system.

It owns point-in-time model research, validation, decision-record prototypes, and model outputs for:

1. market state / regime modeling;
2. dynamic strategy selection;
3. signal quality and trade-outcome prediction;
4. option contract / expression selection;
5. event shock and abnormal-activity overlays;
6. portfolio risk, sizing, and execution-gate modeling.

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

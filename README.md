# trading-model

`trading-model` is the offline modeling repository for the current eight-layer trading decision stack.

It owns point-in-time model research, model-local generators/evaluators, promotion evidence, and model outputs. It does **not** own raw source acquisition, global registry authority, durable storage policy, dashboards, live/paper order placement, broker/account mutation, generated runtime artifacts committed to Git, or secrets.

## Current Route

```text
MarketRegimeModel
  -> market_context_state

SectorContextModel
  -> sector_context_state

anonymous target candidate builder + TargetStateVectorModel
  -> anonymous_target_feature_vector
  -> target_context_state

EventOverlayModel
  -> event_context_vector

AlphaConfidenceModel
  -> alpha_confidence_vector

PositionProjectionModel
  -> position_projection_vector

UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector

OptionExpressionModel
  -> option_expression_plan / expression_vector
```

Layer 1 describes broad market state only. Layer 2 describes sector/industry tradability under that market state. Layer 3 is the first target-state layer and keeps ticker/company identity out of model-facing fitting vectors. Layers 4-8 convert target state into event context, alpha confidence, projected position state, direct-underlying action thesis, and option-expression choice. Broker orders and account mutation stay outside this repository.

## Top-Level Structure

```text
docs/        Scope, current layer contracts, architecture, decisions, tasks, and promotion readiness.
src/         Importable model packages and shared governance/promotion helpers.
scripts/     Stable executable entrypoints for model generation, evaluation, review, and governance.
tests/       First-party unit tests and CLI smoke checks using local rows/fake cursors.
```

`src/` owns reusable model logic. `scripts/` may import `src/`; `src/` must not import `scripts/`.

## Implementation Packages

```text
src/models/model_01_market_regime/        MarketRegimeModel.
src/models/model_02_sector_context/       SectorContextModel.
src/models/model_03_target_state_vector/  TargetStateVectorModel and anonymous target candidate preprocessing.
src/models/model_04_event_overlay/        EventOverlayModel.
src/models/model_05_alpha_confidence/     AlphaConfidenceModel.
src/models/model_06_position_projection/  PositionProjectionModel.
src/models/model_07_underlying_action/    UnderlyingActionModel.
src/models/model_08_option_expression/    OptionExpressionModel.
src/model_governance/                     Shared evaluation, promotion, SQL, and local-layer helpers.
```

## Script Entry Points

Model-specific scripts live under `scripts/models/model_NN_<slug>/` and follow the same layer order. Each layer exposes generation/evaluation/review entrypoints where implemented. Shared governance scripts live under `scripts/model_governance/`.

Important paths:

```text
scripts/models/model_01_market_regime/
scripts/models/model_02_sector_context/
scripts/models/model_03_target_state_vector/
scripts/models/model_04_event_overlay/
scripts/models/model_05_alpha_confidence/
scripts/models/model_06_position_projection/
scripts/models/model_07_underlying_action/
scripts/models/model_08_option_expression/
scripts/models/review_layers_03_08_promotion_closeout.py
scripts/model_governance/
```

Layer 1-3 scripts include SQL-backed evaluation/review paths where current substrate exists. Layer 4-8 scripts are local JSON/JSONL-safe entrypoints until production evaluation substrate exists. No script may imply production promotion unless the accepted governance evidence package and reviewed activation path are present.

## Docs Spine

```text
docs/00_scope.md
docs/01_context.md
docs/02_layer_01_market_regime.md
docs/03_layer_02_sector_context.md
docs/04_layer_03_target_state_vector.md
docs/05_layer_04_event_overlay.md
docs/06_layer_05_alpha_confidence.md
docs/07_layer_06_position_projection.md
docs/08_layer_07_underlying_action.md
docs/09_layer_08_option_expression.md
docs/80_task.md
docs/81_decision.md
docs/82_memory.md
docs/90_system_model_architecture_rfc.md
docs/91_model_decomposition.md
docs/92_vector_taxonomy.md
docs/93_state_vector_feature_registry.md
docs/94_model_stack_closeout.md
docs/95_promotion_readiness.md
docs/96_promotion_closeout.md
docs/97_historical_dataset_scope.md
```

Layer workflow and acceptance live in the numbered layer files. Architecture and decomposition docs describe the current route, not historical detours.

## Platform Boundaries

- `trading-data` owns provider/API/web/file acquisition, feeds, sources, deterministic data features, and SQL/artifact handoff inputs.
- `trading-model` owns offline model outputs, validation, and promotion evidence.
- `trading-manager` owns registry authority, shared contracts, templates, helper policy, control-plane contracts, and lifecycle routing.
- `trading-storage` owns durable storage layout, retention, backup, and restore policy.
- Execution-side repositories own broker/account mutation and live/paper order placement.

Any new shared helper, template, field, status, type, config key, artifact contract, or vocabulary discovered here must be routed through `trading-manager` before another repository depends on it.

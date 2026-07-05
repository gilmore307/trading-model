# trading-model

`trading-model` is the offline modeling repository for the current five-model trading decision stack.

It owns point-in-time model research, model-local generators/evaluators, promotion evidence, and model outputs. It does **not** own raw source acquisition, global registry authority, durable storage policy, dashboards, live/paper order placement, broker/account mutation, generated runtime artifacts committed to Git, or secrets.

## Current Route

The accepted topology is five model contracts:

```text
M01 Background Context
M02 Target State / Selection
M03 Event State / Event Conditioning
M04 Unified Decision
M05 Option Expression
```

```text
M01 Background Context
  -> background_context_state
     (broad market + sector/industry background)

M02 Target State / Selection
  -> target_context_state
     (anonymous target candidate construction remains inside this boundary)

M03 Event State / Event Conditioning
  -> event_state_vector

M04 Unified Decision
  -> unified_decision_vector
     (structured edge, risk, exposure, and direct-underlying action heads)

M05 Option Expression
  -> optional option_expression_plan / expression_vector
```

M01 owns broad market and sector/industry background as one model. M02 owns target selection/state and keeps ticker/company identity out of model-facing fitting vectors. M03 owns accepted event-state conditioning and event-effect-model projection. M04 owns the final direct-underlying posterior probability surface and derives structured edge, risk, exposure, and action summaries. M05 owns optional option-expression probability surfaces after direct-underlying intent exists. Broker orders, account mutation, and component-control execution stay outside this repository.

The accepted learned-model route is replayable cumulative learning with one active learned scheme per layer:

```text
M01 -> continual_gru_context_estimator
M02 -> continual_pairwise_residual_mlp_target_ranker
M03 -> continual_gru_event_risk_scorer
M04 -> continual_residual_mlp_policy_value
M05 -> continual_residual_mlp_option_chain_ranker
```

M01 and M03 use CPU-friendly short-window GRU schemes because they need sequence memory and state persistence. M02, M04, and M05 use residual-MLP ranking/policy schemes because they need nonlinear dense-state interaction over anonymous target, decision, and option-chain state. Every learned scheme must be checkpointable, replayable, rollbackable, target-anonymous, and point-in-time safe.

## Top-Level Structure

```text
docs/        Scope, current five-model contracts, architecture, decisions, tasks, and promotion readiness.
src/         Importable model packages and shared governance/promotion helpers.
scripts/     Stable executable entrypoints for model generation, evaluation, review, and governance.
tests/       First-party unit tests and CLI smoke checks using local rows/fake cursors.
```

`src/` owns reusable model logic. `scripts/` may import `src/`; `src/` must not import `scripts/`.

## Runtime Configuration

Install Python dependencies from `requirements.txt`. SQL-backed governance/generation paths require `psycopg[binary]`; pure fixture/local tests do not import it eagerly.

Runtime path defaults preserve the OpenClaw `/root/projects` layout but can be overridden for downloaded copies or CI with `TRADING_MODEL_ROOT`, `TRADING_DATA_ROOT`, `TRADING_MANAGER_ROOT`, `TRADING_STORAGE_ROOT`, `TRADING_PROJECTS_ROOT`, `TRADING_SECRET_ROOT`, `TRADING_MODEL_DATABASE_URL`, and `TRADING_MODEL_DATABASE_URL_FILE`.

## Implementation Packages

```text
src/models/model_sequence.py                       M01-M05 display/order metadata.
src/models/model_01_background_context/            M01 Background Context.
src/models/model_02_target_state/                  M02 Target State.
src/models/model_03_event_state/                   M03 Event State.
src/models/model_04_unified_decision/              M04 Unified Decision.
src/models/model_05_option_expression/             M05 Option Expression.
src/models/model_03_event_state/event_governance/  M03 event taxonomy/effect-model evidence tooling.
src/model_governance/                     Shared evaluation, promotion, SQL, and current-model helpers.
```

## Script Entry Points

Model-specific scripts should live under `scripts/models/model_NN_<five_model_slug>/` and follow the five-model order. Shared governance scripts live under `scripts/model_governance/`.

Important paths:

```text
scripts/models/model_01_background_context/
scripts/models/model_02_target_state/
scripts/models/model_03_event_state/
scripts/models/model_04_unified_decision/
scripts/models/model_05_option_expression/
scripts/models/model_03_event_state/event_governance/
scripts/models/run_current_model_chain.py
scripts/models/run_current_model_historical_evaluation.py
scripts/models/audit_model_output_tables.py
scripts/models/run_model_output_quality_gate.py
scripts/model_governance/
```

Only the five-model script paths above are maintained current entrypoints. No script may imply production promotion unless the accepted governance evidence package and reviewed activation path are present.

## Docs Spine

```text
docs/00_scope.md
docs/01_context.md
docs/02_architecture.md
docs/03_contracts.md
docs/04_task.md
docs/05_decision.md
docs/06_memory.md
docs/10_model_01_background_context.md
docs/11_model_02_target_state.md
docs/12_model_03_event_state.md
docs/13_model_04_unified_decision.md
docs/14_model_05_option_expression.md
docs/20_model_decomposition.md
docs/21_vector_taxonomy.md
docs/22_state_vector_feature_registry.md
docs/23_model_learning_design.md
docs/24_model_framework_readiness.md
docs/30_promotion_readiness.md
docs/31_promotion_acceptance.md
docs/32_model_output_quality.md
docs/33_model_data_tables.md
docs/40_historical_dataset_scope.md
docs/41_realtime_decision_handoff.md
docs/50_activity_price_relationship_study.md
docs/51_event_family_scouting.md
docs/52_earnings_guidance_event_family_packet.md
docs/53_event_state_final_judgment.md
```

Model workflow and acceptance live in the numbered model files. Architecture and decomposition docs describe the current five-model route, not historical detours.

## Platform Boundaries

- `trading-data` owns provider/API/web/file acquisition, feeds, sources, deterministic data features, and SQL/artifact handoff inputs.
- `trading-model` owns offline model outputs, validation, and promotion evidence.
- `trading-manager` owns registry authority, shared contracts, templates, helper policy, control-plane contracts, and lifecycle routing.
- `trading-storage` owns durable storage layout, retention, backup, and restore policy.
- Execution-side repositories own broker/account mutation and live/paper order placement.

Any new shared helper, template, field, status, type, config key, artifact contract, or vocabulary discovered here must be routed through `trading-manager` before another repository depends on it.

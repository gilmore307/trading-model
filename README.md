# trading-model

`trading-model` is the offline modeling repository for the current ten-layer trading decision stack.

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

EventFailureRiskModel
  -> event_failure_risk_vector

AlphaConfidenceModel
  -> alpha_confidence_vector

DynamicRiskPolicyModel
  -> dynamic_risk_policy_state

PositionProjectionModel
  -> position_projection_vector

UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector

TradingGuidanceModel / OptionExpressionModel
  -> trading_guidance_record plus optional option_expression_plan / expression_vector

EventRiskGovernor / EventIntelligenceOverlay
  -> event_risk_intervention / event-adjusted risk guidance
```

Layer 1 describes broad market state only. Layer 2 describes sector/industry tradability under that market state. Layer 3 is the first target-state layer and keeps ticker/company identity out of model-facing fitting vectors. Layer 4 adds reviewed event-failure-risk conditioning. Layers 5-8 convert target state and reviewed failure-risk conditioning into alpha confidence, dynamic risk policy, projected position state, and a direct-underlying action thesis. Layer 9 composes optional offline trading guidance and option-expression context from that thesis. Layer 10 applies event-risk governance to the direct-underlying/spot thesis, with Layer 9 context attached only when available. Broker orders and account mutation stay outside this repository.

## Top-Level Structure

```text
docs/        Scope, current layer contracts, architecture, decisions, tasks, and promotion readiness.
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
src/models/model_01_market_regime/        MarketRegimeModel.
src/models/model_02_sector_context/       SectorContextModel.
src/models/model_03_target_state_vector/  TargetStateVectorModel and anonymous target candidate preprocessing.
src/models/model_04_event_failure_risk/   EventFailureRiskModel.
src/models/model_05_alpha_confidence/     AlphaConfidenceModel.
src/models/model_06_dynamic_risk_policy/  DynamicRiskPolicyModel.
src/models/model_07_position_projection/  PositionProjectionModel.
src/models/model_08_underlying_action/    UnderlyingActionModel.
src/models/model_09_option_expression/    OptionExpressionModel package for Layer 9 trading guidance.
src/models/model_10_event_risk_governor/  EventRiskGovernor.
src/model_governance/                     Shared evaluation, promotion, SQL, and local-layer helpers.
```

## Script Entry Points

Model-specific scripts live under `scripts/models/model_NN_<slug>/` and follow the same layer order. Each layer exposes generation/evaluation/review entrypoints where implemented. Shared governance scripts live under `scripts/model_governance/`.

Important paths:

```text
scripts/models/model_01_market_regime/
scripts/models/model_02_sector_context/
scripts/models/model_03_target_state_vector/
scripts/models/model_04_event_failure_risk/
scripts/models/model_05_alpha_confidence/
scripts/models/model_06_dynamic_risk_policy/
scripts/models/model_07_position_projection/
scripts/models/model_08_underlying_action/
scripts/models/model_09_option_expression/
scripts/models/model_10_event_risk_governor/
scripts/models/audit_model_output_tables.py
scripts/models/run_model_output_quality_gate.py
scripts/models/review_layers_03_08_promotion_acceptance.py
scripts/model_governance/
```

Layer 1-3 scripts include SQL-backed evaluation/review paths where current substrate exists. Layer 1 also exposes `diagnose_model_01_market_regime_substrate.py`, a read-only source/feature/model substrate diagnostic for promotion-readiness triage before regeneration planning. `scripts/models/audit_model_output_tables.py` audits all ten model output/support table families for empty or sparse columns without mutating SQL, and `scripts/models/run_model_output_quality_gate.py` turns that audit into a pass/block decision for post-generation acceptance. Layer 4 event-failure-risk scripts and Layer 10 event-risk scripts use the physical `model_04_event_failure_risk` and `model_10_event_risk_governor` surfaces. No script may imply production promotion unless the accepted governance evidence package and reviewed activation path are present.

## Docs Spine

```text
docs/00_scope.md
docs/01_context.md
docs/02_architecture.md
docs/03_contracts.md
docs/04_task.md
docs/05_decision.md
docs/06_memory.md
docs/10_layer_01_market_regime.md
docs/11_layer_02_sector_context.md
docs/12_layer_03_target_state_vector.md
docs/13_layer_04_event_failure_risk.md
docs/14_layer_05_alpha_confidence.md
docs/15_layer_06_dynamic_risk_policy.md
docs/16_layer_07_position_projection.md
docs/17_layer_08_underlying_action.md
docs/18_layer_09_trading_guidance.md
docs/19_layer_10_event_risk_governor.md
docs/20_model_decomposition.md
docs/21_vector_taxonomy.md
docs/22_state_vector_feature_registry.md
docs/30_promotion_readiness.md
docs/31_promotion_acceptance.md
docs/32_model_output_quality.md
docs/40_historical_dataset_scope.md
docs/41_realtime_decision_handoff.md
docs/50_activity_price_relationship_study.md
docs/51_event_family_scouting.md
docs/52_earnings_guidance_event_family_packet.md
docs/53_event_layer_final_judgment.md
```

Layer workflow and acceptance live in the numbered layer files. Architecture and decomposition docs describe the current route, not historical detours.

## Platform Boundaries

- `trading-data` owns provider/API/web/file acquisition, feeds, sources, deterministic data features, and SQL/artifact handoff inputs.
- `trading-model` owns offline model outputs, validation, and promotion evidence.
- `trading-manager` owns registry authority, shared contracts, templates, helper policy, control-plane contracts, and lifecycle routing.
- `trading-storage` owns durable storage layout, retention, backup, and restore policy.
- Execution-side repositories own broker/account mutation and live/paper order placement.

Any new shared helper, template, field, status, type, config key, artifact contract, or vocabulary discovered here must be routed through `trading-manager` before another repository depends on it.

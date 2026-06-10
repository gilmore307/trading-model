# Model Data Tables

Status: current inventory for model-owned SQL surfaces

## Purpose

This document is the first pass over `trading-model` data tables. It separates model-owned tables from upstream data tables and manager-owned lifecycle tables so future cleanup can happen without moving responsibilities across repository boundaries.

## Ownership Boundary

`trading-data` owns raw source acquisition, normalized source tables, and deterministic feature tables. `trading-model` may read those tables but must not treat them as model-owned schema.

`trading-model` owns model-generation output tables, their `_explainability` support tables, their `_diagnostics` support tables, and model-local evaluation evidence tables.

Model table surfaces follow the shared owner-domain-stage pattern:

```text
trading_model.mNN_<domain_slug>_model_generation
trading_model.mNN_<domain_slug>_model_generation_explainability
trading_model.mNN_<domain_slug>_model_generation_diagnostics
```

Old `trading_model.model_NN_*` names are migration debt, not current planning names.

`trading-evaluation` owns promotion-readiness records. `trading-execution` owns runtime activation records, rollback refs, active-pointer writes, and runtime lifecycle routing. `trading-manager` owns request scheduling and shared registry authority. Promotion evidence rows may be produced here, but activation state must not live here.

Execution-side repositories own broker, account, order, fill, and buying-power mutation. No model table is an order table.

## Output Table Families

Each accepted model layer has one narrow primary table and two support tables:

| Layer | Primary table | Explainability table | Diagnostics table |
|---|---|---|---|
| M01 Market Regime | `trading_model.m01_market_regime_model_generation` | `trading_model.m01_market_regime_model_generation_explainability` | `trading_model.m01_market_regime_model_generation_diagnostics` |
| M02 Sector Context | `trading_model.m02_sector_context_model_generation` | `trading_model.m02_sector_context_model_generation_explainability` | `trading_model.m02_sector_context_model_generation_diagnostics` |
| M03 Target State | `trading_model.m03_target_state_vector_model_generation` | `trading_model.m03_target_state_vector_model_generation_explainability` | `trading_model.m03_target_state_vector_model_generation_diagnostics` |
| M04 Event Failure Risk | `trading_model.m04_event_failure_risk_model_generation` | `trading_model.m04_event_failure_risk_model_generation_explainability` | `trading_model.m04_event_failure_risk_model_generation_diagnostics` |
| M05 Alpha Confidence | `trading_model.m05_alpha_confidence_model_generation` | `trading_model.m05_alpha_confidence_model_generation_explainability` | `trading_model.m05_alpha_confidence_model_generation_diagnostics` |
| M06 Dynamic Risk Policy | `trading_model.m06_dynamic_risk_policy_model_generation` | `trading_model.m06_dynamic_risk_policy_model_generation_explainability` | `trading_model.m06_dynamic_risk_policy_model_generation_diagnostics` |
| M07 Position Projection | `trading_model.m07_position_projection_model_generation` | `trading_model.m07_position_projection_model_generation_explainability` | `trading_model.m07_position_projection_model_generation_diagnostics` |
| M08 Underlying Action | `trading_model.m08_underlying_action_model_generation` | `trading_model.m08_underlying_action_model_generation_explainability` | `trading_model.m08_underlying_action_model_generation_diagnostics` |
| M09 Option Expression | `trading_model.m09_option_expression_model_generation` | `trading_model.m09_option_expression_model_generation_explainability` | `trading_model.m09_option_expression_model_generation_diagnostics` |
| M10 Event Risk Governor | `trading_model.m10_event_risk_governor_model_generation` | `trading_model.m10_event_risk_governor_model_generation_explainability` | `trading_model.m10_event_risk_governor_model_generation_diagnostics` |

Primary tables are the downstream dependency surface. Explainability tables own human-review internals and nested vectors. Diagnostics tables own acceptance, monitoring, gating evidence, and reason-code detail.

The canonical audit list is `model_governance.model_output_audit.MODEL_OUTPUT_TABLES`; it covers all 30 tables above.

## Current Input Dependencies

The following dependencies are table-level dependencies in the current SQL generation paths, not a claim that every dependency is already production-promotable.

| Model | Current upstream table dependencies |
|---|---|
| M01 | `trading_data.m01_market_regime_feature_generation` |
| M02 | `trading_data.m02_sector_context_feature_generation`, `trading_model.m01_market_regime_model_generation` |
| M03 | `trading_data.m03_target_state_vector_feature_generation`, `trading_data.m03_target_state_vector_data_acquisition`, `trading_model.m01_market_regime_model_generation`, `trading_model.m02_sector_context_model_generation`, reviewed target-context mapping evidence |
| M04 | `trading_model.m03_target_state_vector_model_generation`; optional `trading_model.event_strategy_failure_gate`; absent event-failure evidence produces neutral no-reviewed-event-risk rows |
| M05 | `trading_model.m04_event_failure_risk_model_generation`, `trading_model.m03_target_state_vector_model_generation`, `trading_data.m03_target_state_vector_data_acquisition`, `trading_model.m02_sector_context_model_generation`, `trading_model.m01_market_regime_model_generation` |
| M06 | `trading_model.m05_alpha_confidence_model_generation`, `trading_model.m01_market_regime_model_generation`, `trading_model.m04_event_failure_risk_model_generation` |
| M07 | `trading_model.m05_alpha_confidence_model_generation`, `trading_model.m06_dynamic_risk_policy_model_generation` |
| M08 | `trading_model.m07_position_projection_model_generation`, `trading_model.m05_alpha_confidence_model_generation`, `trading_data.m03_target_state_vector_data_acquisition` |
| M09 | `trading_model.m08_underlying_action_model_generation`, `trading_data.m03_target_state_vector_data_acquisition`, optional `trading_model.m08_underlying_action_model_generation_explainability`, optional `trading_data.m09_option_expression_feature_generation` |
| M10 | `trading_data.m10_event_risk_governor_data_acquisition`, `trading_data.m03_target_state_vector_data_acquisition`, `trading_model.m03_target_state_vector_model_generation`, optional `trading_model.m03_target_state_vector_model_generation_explainability` |

## Evaluation And Governance Tables

`model_governance.evaluation.schema` owns these model-local evidence tables:

| Table | Role |
|---|---|
| `trading_model.model_dataset_request` | Dataset request evidence for a model evaluation run. |
| `trading_model.model_dataset_snapshot` | Point-in-time dataset snapshot identity, source table, time span, row count, and hashes. |
| `trading_model.model_dataset_split` | Chronological split windows under a dataset snapshot. |
| `trading_model.model_eval_label` | Point-in-time labels used for evaluation. |
| `trading_model.model_eval_run` | Model evaluation run metadata and status. |
| `trading_model.model_promotion_metric` | Promotion-readiness metrics derived from evaluation runs. |

These tables support promotion evidence. They do not approve promotion by themselves and must not store activation state.

## Review Findings

- Corrected in this pass: `docs/32_model_output_quality.md` now refers to the current six-model table families and retained migration-source table families.
- Corrected in this pass: `docs/02_architecture.md` now treats retired ten-layer tables as migration-source implementation surfaces only.
- Retired SQL generation paths may consume their older upstream model/source tables while migration is underway. Missing upstream evidence should reduce produced rows or block the stage instead of silently manufacturing a complete model path from placeholder state.

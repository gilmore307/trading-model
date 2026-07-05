# Model Data Tables

Status: current inventory for model-owned SQL surfaces

## Purpose

This document is the first pass over `trading-model` data tables. It separates model-owned tables from upstream data tables and manager-owned lifecycle tables so future cleanup can happen without moving responsibilities across repository boundaries.

## Ownership Boundary

`trading-data` owns raw source acquisition, normalized source tables, and deterministic feature tables. `trading-model` may read those tables but must not treat them as model-owned schema.

`trading-model` owns model-generation output tables, their `_explainability` support tables, their `_diagnostics` support tables, and model-local evaluation evidence tables.

Current model table surfaces follow the accepted five-model surface names:

```text
trading_model.model_NN_<model_slug>
trading_model.model_NN_<model_slug>_explainability
trading_model.model_NN_<model_slug>_diagnostics
```

The current audit scope is the M01-M05 output family.

`trading-evaluation` owns promotion-readiness records. `trading-execution` owns runtime activation records, rollback refs, active-pointer writes, and runtime lifecycle routing. `trading-manager` owns request scheduling and shared registry authority. Promotion evidence rows may be produced here, but activation state must not live here.

Execution-side repositories own broker, account, order, fill, and buying-power mutation. No model table is an order table.

## Output Table Families

Each accepted current model has one narrow primary table and two support tables:

| Model | Primary table | Explainability table | Diagnostics table |
|---|---|---|---|
| M01 Background Context | `trading_model.model_01_background_context` | `trading_model.model_01_background_context_explainability` | `trading_model.model_01_background_context_diagnostics` |
| M02 Target State | `trading_model.model_02_target_state` | `trading_model.model_02_target_state_explainability` | `trading_model.model_02_target_state_diagnostics` |
| M03 Event State | `trading_model.model_03_event_state` | `trading_model.model_03_event_state_explainability` | `trading_model.model_03_event_state_diagnostics` |
| M04 Unified Decision | `trading_model.model_04_unified_decision` | `trading_model.model_04_unified_decision_explainability` | `trading_model.model_04_unified_decision_diagnostics` |
| M05 Option Expression | `trading_model.model_05_option_expression` | `trading_model.model_05_option_expression_explainability` | `trading_model.model_05_option_expression_diagnostics` |

Primary tables are the downstream dependency surface. Explainability tables own human-review internals and nested vectors. Diagnostics tables own acceptance, monitoring, gating evidence, and reason-code detail.

The canonical current audit list is `model_governance.model_output_audit.CURRENT_MODEL_OUTPUT_TABLES`. `MODEL_OUTPUT_TABLES` is an alias for that current list.

## Current Input Dependencies

The following dependencies are contract-level dependencies for the accepted current stack, not a claim that every dependency is already production-promotable SQL.

| Model | Current upstream dependency class |
|---|---|
| M01 | Broad market, sector/industry, liquidity, volatility, breadth, correlation, dispersion, and macro-sensitive point-in-time features. |
| M02 | M01 `background_context_state` plus anonymous target-local features, target eligibility, and candidate-policy evidence. |
| M03 | M01/M02 state plus accepted M03 event-family contracts, frozen event observations, and reviewed event applicability evidence. |
| M04 | M01/M02/M03 states plus quality, portfolio/risk, cost/friction, quote/liquidity/borrow, exposure, and policy-gate context. |
| M05 | M04 direct-underlying intent, M03 event-state option-impact channels, point-in-time option-chain candidates, option policy, and option exposure context. |

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

- Corrected in this pass: `docs/32_model_output_quality.md` now refers to the current five-model table families.
- Corrected in this pass: `docs/02_architecture.md` now treats the current M01-M05 packages as the only active model implementation surface.
- Retired SQL generation paths may consume their older upstream model/source tables while migration is underway. Missing upstream evidence should reduce produced rows or block the stage instead of silently manufacturing a complete model path from placeholder state.

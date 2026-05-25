# Model Data Tables

Status: current inventory for model-owned SQL surfaces

## Purpose

This document is the first pass over `trading-model` data tables. It separates model-owned tables from upstream data tables and manager-owned lifecycle tables so future cleanup can happen without moving responsibilities across repository boundaries.

## Ownership Boundary

`trading-data` owns raw source acquisition, normalized source tables, and deterministic feature tables. `trading-model` may read those tables but must not treat them as model-owned schema.

`trading-model` owns model-generation output tables, their `_explainability` support tables, their `_diagnostics` support tables, and model-local evaluation evidence tables.

New model table surfaces follow the shared owner-domain-stage pattern:

```text
trading_model.mNN_<domain_slug>_model_generation
trading_model.mNN_<domain_slug>_model_generation_explainability
trading_model.mNN_<domain_slug>_model_generation_diagnostics
```

Existing `trading_model.model_NN_*` tables remain compatibility surfaces until a reviewed migration replaces them. Do not use the older `model_NN_*` pattern for newly planned tables.

`trading-manager` owns durable promotion decisions, activation records, rollback records, runtime lifecycle routing, and shared registry authority. Promotion evidence rows may be produced here, but activation state must not live here.

Execution-side repositories own broker, account, order, fill, and buying-power mutation. No model table is an order table.

## Output Table Families

Each accepted model layer has one narrow primary table and two support tables:

| Layer | Primary table | Explainability table | Diagnostics table |
|---|---|---|---|
| M01 Market Regime | `trading_model.model_01_market_regime` | `trading_model.model_01_market_regime_explainability` | `trading_model.model_01_market_regime_diagnostics` |
| M02 Sector Context | `trading_model.model_02_sector_context` | `trading_model.model_02_sector_context_explainability` | `trading_model.model_02_sector_context_diagnostics` |
| M03 Target State | `trading_model.model_03_target_state_vector` | `trading_model.model_03_target_state_vector_explainability` | `trading_model.model_03_target_state_vector_diagnostics` |
| M04 Event Failure Risk | `trading_model.model_04_event_failure_risk` | `trading_model.model_04_event_failure_risk_explainability` | `trading_model.model_04_event_failure_risk_diagnostics` |
| M05 Alpha Confidence | `trading_model.model_05_alpha_confidence` | `trading_model.model_05_alpha_confidence_explainability` | `trading_model.model_05_alpha_confidence_diagnostics` |
| M06 Dynamic Risk Policy | `trading_model.model_06_dynamic_risk_policy` | `trading_model.model_06_dynamic_risk_policy_explainability` | `trading_model.model_06_dynamic_risk_policy_diagnostics` |
| M07 Position Projection | `trading_model.model_07_position_projection` | `trading_model.model_07_position_projection_explainability` | `trading_model.model_07_position_projection_diagnostics` |
| M08 Underlying Action | `trading_model.model_08_underlying_action` | `trading_model.model_08_underlying_action_explainability` | `trading_model.model_08_underlying_action_diagnostics` |
| M09 Option Expression | `trading_model.model_09_option_expression` | `trading_model.model_09_option_expression_explainability` | `trading_model.model_09_option_expression_diagnostics` |
| M10 Event Risk Governor | `trading_model.model_10_event_risk_governor` | `trading_model.model_10_event_risk_governor_explainability` | `trading_model.model_10_event_risk_governor_diagnostics` |

Primary tables are the downstream dependency surface. Explainability tables own human-review internals and nested vectors. Diagnostics tables own acceptance, monitoring, gating evidence, and reason-code detail.

The canonical audit list is `model_governance.model_output_audit.MODEL_OUTPUT_TABLES`; it covers all 30 tables above.

## Current Input Dependencies

The following dependencies are table-level dependencies in the current SQL generation paths, not a claim that every dependency is already production-promotable.

| Model | Current upstream table dependencies |
|---|---|
| M01 | `trading_data.feature_01_market_regime` |
| M02 | `trading_data.feature_02_sector_context`, `trading_model.model_01_market_regime` |
| M03 | `trading_data.feature_03_target_state_vector`, `trading_data.source_03_target_state`, `trading_model.model_01_market_regime`, `trading_model.model_02_sector_context`; optional `trading_data.source_02_target_candidate_holdings` for ETF-holding sector context fallback |
| M04 | `trading_model.model_03_target_state_vector`; optional `trading_model.event_strategy_failure_gate`; absent event-failure evidence produces neutral no-reviewed-event-risk rows |
| M05 | `trading_model.model_04_event_failure_risk`, `trading_model.model_03_target_state_vector`, `trading_data.source_03_target_state`, `trading_model.model_02_sector_context`, `trading_model.model_01_market_regime` |
| M06 | `trading_model.model_05_alpha_confidence`; broader market/systemic/portfolio context is currently fixture/default scaffold state in the SQL path |
| M07 | `trading_model.model_05_alpha_confidence`; current SQL path does not yet join `trading_model.model_06_dynamic_risk_policy` even though the accepted model contract says dynamic risk policy should condition position projection |
| M08 | `trading_model.model_07_position_projection`, `trading_model.model_05_alpha_confidence` |
| M09 | `trading_model.model_08_underlying_action`, `trading_data.source_03_target_state`, optional `trading_model.model_08_underlying_action_explainability`, optional `trading_data.feature_09_option_expression` |
| M10 | `trading_data.source_10_event_risk_governor`, `trading_data.source_03_target_state`, `trading_model.model_03_target_state_vector`, optional `trading_model.model_03_target_state_vector_explainability` |

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

- Corrected in this pass: `docs/32_model_output_quality.md` now refers to `model_01_*` through `model_10_*`, because the audit code already covers all ten model table families.
- Corrected in this pass: `docs/02_architecture.md` now treats `model_10_*` as part of the layer-specific model implementation surface; the `50_*` docs remain event-family research detail inside the Layer 10 package.
- The M07 SQL generation path currently bypasses `model_06_dynamic_risk_policy` and injects default risk-budget/policy state. That is acceptable as a scaffold only; it is not the final table dependency shape for production evidence.
- The M06 SQL generation path currently derives dynamic risk policy only from `model_05_alpha_confidence` plus scaffold state. Before production promotion, this path needs explicit market/systemic/portfolio context evidence or a documented reviewed exception.

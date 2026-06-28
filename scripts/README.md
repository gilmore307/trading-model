# scripts

Executable entrypoints for `trading-model`.

Directory boundary:

- `models/` owns model-specific entrypoints, organized by the current six-model `model_NN_<slug>/` contract.
- `model_governance/` owns shared governance/development schema entrypoints.

Scripts are the runtime boundary. Reusable model logic belongs in `src/`; scripts may import `src/`, but `src/` must not import scripts.

## Model entrypoints

- `models/model_01_background_context/` — current home for M01 Background Context entrypoints.
- `models/model_02_target_state/` — current home for M02 Target State entrypoints.
- `models/model_03_event_state/` — current home for M03 Event State entrypoints.
- `models/model_04_unified_decision/` — current home for M04 Unified Decision entrypoints.
- `models/model_05_option_expression/` — current home for M05 Option Expression entrypoints.
- `models/model_06_residual_event_governance/` — current home for M06 Residual Event Governance entrypoints.
- - `models/audit_model_output_tables.py` emits a read-only `model_output_table_quality_audit` over current and model output/support table families.
- `models/run_current_model_chain.py` is a local fixture smoke gate for the current M01-M06 contracts. It does not produce production promotion evidence.
- `models/run_current_model_historical_evaluation.py` runs the current M01-M06 chain over bounded point-in-time historical rows, builds chronological folds and mature future-return labels, and may train a local cumulative residual-MLP utility baseline artifact for chain-level evidence. It is read-only evidence generation and never promotes or activates a model.
- `models/run_model_output_quality_gate.py` emits `model_output_quality_gate` and exits non-zero when post-generation primary output defects should block acceptance.
- `models/review_current_model_promotion_acceptance.py` reviews blocked promotion acceptance for current M03-M06 contracts when production evaluation substrate is missing. It must not activate configs or persist manager-control-plane decisions.
- `models/plan_realtime_decision_handoff.py` builds a C-runtime-component-routed `model_realtime_decision_route_plan` from an execution-side realtime model decision input snapshot without running models or activating production configs.
- `models/validate_realtime_decision_handoff.py` validates realtime decision input snapshots or route plans without side effects.

## Shared governance entrypoints

- `model_governance/ensure_model_governance_schema.py` creates generic `trading_model` model-evidence/evaluation tables through `psql`; use `--dry-run` to print DDL without touching PostgreSQL. Promotion decision/activation/rollback tables are not model-owned.
- `model_governance/clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.

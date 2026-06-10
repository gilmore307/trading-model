# scripts

Executable entrypoints for `trading-model`.

Directory boundary:

- `models/` owns model-specific entrypoints, organized by `model_NN_<slug>/`.
- `model_governance/` owns shared governance/development schema entrypoints.

Scripts are the runtime boundary. Reusable model logic belongs in `src/`; scripts may import `src/`, but `src/` must not import scripts.

## Model entrypoints

- `models/model_01_market_regime/`
  - `generate_model_01_market_regime.py` reads `trading_data.m01_market_regime_feature_generation`, writes `trading_model.m01_market_regime_model_generation`, and writes explainability/diagnostics support rows.
  - `evaluate_model_01_market_regime.py` builds MarketRegimeModel evaluation evidence from fixture/local rows or read-only PostgreSQL rows with `--from-database`.
  - `review_market_regime_promotion.py` builds evaluation-backed promotion candidate evidence and a review artifact; manager-control-plane decision/activation stays in `trading-manager`.
  - `run_market_regime_development_smoke.py` runs a deterministic development DB smoke chain under the isolated `trading_model_development_smoke` schema; it requires explicit `--database-url` plus the database-mutation confirmation token and cleans temporary tables by default.
- `models/model_02_sector_context/`
  - `generate_model_02_sector_context.py` reads Layer 2 features plus Layer 1 context and writes `trading_model.m02_sector_context_model_generation` plus support rows.
  - `evaluate_model_02_sector_context.py` builds SectorContextModel evaluation evidence from fixture/local rows or read-only PostgreSQL rows with `--from-database`.
  - `review_sector_context_promotion.py` builds conservative promotion review evidence/artifacts.
- `models/model_03_target_state_vector/`
  - `generate_model_03_target_state_vector.py` generates `model_03_target_state_vector` rows from local/SQL-backed Layer 3 feature rows.
  - `evaluate_model_03_target_state_vector.py` builds baseline-ladder evaluation evidence.
  - `review_target_state_vector_promotion.py` reviews local/fixture evidence conservatively.
  - `review_target_state_vector_production_substrate.py` reviews the real Layer 3 production-evaluation substrate when present.
- `models/model_04_event_failure_risk/`
  - `generate_model_04_event_failure_risk.py`, `evaluate_model_04_event_failure_risk.py`, and `review_event_failure_risk_promotion.py` are local JSON/JSONL-safe EventFailureRiskModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
  - `build_layer4_focus_pool_inputs.py` builds Layer 4 input rows from accepted Layer 10 focus-pool replay evidence while filtering out rejected event families and preserving Layer 10 event parameters as frozen inputs.
- `models/model_05_alpha_confidence/`
  - `train_model_05_alpha_confidence.py`, `generate_model_05_alpha_confidence.py`, `evaluate_model_05_alpha_confidence.py`, and `review_alpha_confidence_promotion.py` are local JSON/JSONL-safe AlphaConfidenceModel training, generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows. The trained Layer 5 path uses a LightGBM GBDT artifact and emits a normalized after-cost alpha score where `0.5` is neutral.
  - `build_event_conditioned_alpha_contrast.py` builds a diagnostic-only Layer 5 contrast over Layer 4 focus-pool rows from accepted Layer 10 event families: baseline removes Layer 4 event features, the comparison consumes frozen Layer 4 `event_failure_risk_vector`, and the output is marked `diagnostic_not_promotion`.
- `models/model_06_dynamic_risk_policy/`
  - `generate_model_06_dynamic_risk_policy.py`, `evaluate_model_06_dynamic_risk_policy.py`, and `review_dynamic_risk_policy_promotion.py` are local JSON/JSONL-safe DynamicRiskPolicyModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_07_position_projection/`
  - `generate_model_07_position_projection.py`, `evaluate_model_07_position_projection.py`, and `review_position_projection_promotion.py` are local JSON/JSONL-safe PositionProjectionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_08_underlying_action/`
  - `generate_model_08_underlying_action.py`, `evaluate_model_08_underlying_action.py`, and `review_underlying_action_promotion.py` are local JSON/JSONL-safe UnderlyingActionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_09_option_expression/`
  - `generate_model_09_option_expression.py`, `evaluate_model_09_option_expression.py`, and `review_option_expression_promotion.py` are local JSON/JSONL-safe OptionExpressionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows for the reviewed no-provider/no-option path.
- `models/model_10_event_risk_governor/`
  - `generate_model_10_event_risk_governor.py`, `evaluate_model_10_event_risk_governor.py`, and `review_event_risk_governor_promotion.py` are local JSON/JSONL-safe EventRiskGovernor generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
  - `build_event_family_impact_window_all_family_real_input_backtest.py` builds all-family real-input impact-window calibration evidence from retained PIT event candidates and price bars without provider calls, SQL writes, training, activation, broker/account mutation, or artifact deletion.
  - `build_layer_10_fold_completion.py` consolidates fold-scoped packet/source/control/window/replay evidence into the Layer 10 family gate matrix without promotion, activation, broker/account mutation, SQL writes, or artifact deletion.
- `models/audit_model_output_tables.py` emits a read-only `model_output_table_quality_audit` over all ten model output/support table families.
- `models/run_model_output_quality_gate.py` emits `model_output_quality_gate` and exits non-zero when post-generation primary output defects should block acceptance.
- `models/review_layers_03_10_promotion_acceptance.py` emits explicit deferred/blocked promotion evidence artifacts for Layers 3-10. It must not activate configs or persist manager-control-plane decisions.
- `models/plan_realtime_decision_handoff.py` builds a `model_realtime_decision_route_plan` from an execution-side realtime model decision input snapshot without running models or activating production configs.
- `models/validate_realtime_decision_handoff.py` validates realtime decision input snapshots or route plans without side effects.

## Shared governance entrypoints

- `model_governance/ensure_model_governance_schema.py` creates generic `trading_model` model-evidence/evaluation tables through `psql`; use `--dry-run` to print DDL without touching PostgreSQL. Promotion decision/activation/rollback tables are not model-owned.
- `model_governance/clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.

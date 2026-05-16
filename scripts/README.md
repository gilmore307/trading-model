# scripts

Executable entrypoints for `trading-model`.

Directory boundary:

- `models/` owns model-specific entrypoints, organized by `model_NN_<slug>/`.
- `model_governance/` owns shared governance/development schema entrypoints.

Scripts are the runtime boundary. Reusable model logic belongs in `src/`; scripts may import `src/`, but `src/` must not import scripts.

## Model entrypoints

- `models/model_01_market_regime/`
  - `generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime`, writes `trading_model.model_01_market_regime`, and writes explainability/diagnostics support rows.
  - `evaluate_model_01_market_regime.py` builds MarketRegimeModel evaluation evidence from fixture/local rows or read-only PostgreSQL rows with `--from-database`.
  - `review_market_regime_promotion.py` builds evaluation-backed promotion candidate evidence and a review artifact; manager-control-plane decision/activation stays in `trading-manager`.
  - `run_market_regime_development_smoke.py` runs a deterministic development DB smoke chain and cleans temporary tables by default.
- `models/model_02_sector_context/`
  - `generate_model_02_sector_context.py` reads Layer 2 features plus Layer 1 context and writes `trading_model.model_02_sector_context` plus support rows.
  - `evaluate_model_02_sector_context.py` builds SectorContextModel evaluation evidence from fixture/local rows or read-only PostgreSQL rows with `--from-database`.
  - `review_sector_context_promotion.py` builds conservative promotion review evidence/artifacts.
- `models/model_03_target_state_vector/`
  - `generate_model_03_target_state_vector.py` generates `model_03_target_state_vector` rows from local/SQL-backed Layer 3 feature rows.
  - `evaluate_model_03_target_state_vector.py` builds baseline-ladder evaluation evidence.
  - `review_target_state_vector_promotion.py` reviews local/fixture evidence conservatively.
  - `review_target_state_vector_production_substrate.py` reviews the real Layer 3 production-evaluation substrate when present.
- `models/model_08_event_risk_governor/`
  - `generate_model_08_event_risk_governor.py`, `evaluate_model_08_event_risk_governor.py`, and `review_event_risk_governor_promotion.py` are local JSON/JSONL-safe EventRiskGovernor generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_04_alpha_confidence/`
  - `generate_model_04_alpha_confidence.py`, `evaluate_model_04_alpha_confidence.py`, and `review_alpha_confidence_promotion.py` are local JSON/JSONL-safe AlphaConfidenceModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_05_position_projection/`
  - `generate_model_05_position_projection.py`, `evaluate_model_05_position_projection.py`, and `review_position_projection_promotion.py` are local JSON/JSONL-safe PositionProjectionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_06_underlying_action/`
  - `generate_model_06_underlying_action.py`, `evaluate_model_06_underlying_action.py`, and `review_underlying_action_promotion.py` are local JSON/JSONL-safe UnderlyingActionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows.
- `models/model_07_option_expression/`
  - `generate_model_07_option_expression.py`, `evaluate_model_07_option_expression.py`, and `review_option_expression_promotion.py` are local JSON/JSONL-safe OptionExpressionModel generation, evaluation-label, and conservative review entrypoints; generation/evaluation also support SQL-backed `--from-database` workflow rows for the reviewed no-provider/no-option path.
- `models/review_layers_03_08_promotion_closeout.py` emits explicit deferred/blocked promotion evidence artifacts for layers that lack production evaluation substrate. It must not activate configs or persist manager-control-plane decisions.
- `models/plan_realtime_decision_handoff.py` builds a `model_realtime_decision_route_plan` from an execution-side realtime model decision input snapshot without running models or activating production configs.
- `models/validate_realtime_decision_handoff.py` validates realtime decision input snapshots or route plans without side effects.

## Shared governance entrypoints

- `model_governance/ensure_model_governance_schema.py` creates generic `trading_model` model-evidence/evaluation tables through `psql`; use `--dry-run` to print DDL without touching PostgreSQL. Promotion decision/activation/rollback tables are not model-owned.
- `model_governance/clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.

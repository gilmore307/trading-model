# Tasks

This is the active model task ledger. Keep it operational and tied to current gates. Detailed event-family evidence lives in `docs/51_event_family_scouting.md`, `docs/53_event_layer_final_judgment.md`, and the referenced storage artifacts.

## Active Tasks

- Six-model implementation lane: migrate current work to `M01 Background Context`, `M02 Target State`, `M03 Event State`, `M04 Unified Decision`, `M05 Option Expression`, and `M06 Residual Event Governance`. Retired ten-layer packages/scripts may be used as source material only; new current work should target the six model contracts.
- First pilot: implement `M04 Unified Decision` from the retired serial alpha/risk/position/action behavior. The pilot must emit a structured `unified_decision_vector` with edge, risk, exposure, and action heads.
- Model learning redesign: use `docs/23_model_learning_design.md` as the active route for model expansion. Before changing a model implementation, write or verify its objective contract: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, walk-forward metric, leakage test, and downstream consumer.
- Model-output table quality gate: `scripts/models/audit_model_output_tables.py` remains read-only and may inspect current and retained migration-source model output/support table families. `scripts/models/run_model_output_quality_gate.py` converts that audit into a pass/block decision for post-generation acceptance. Both paths are read-only; they do not drop columns or rewrite model rows.
- Event-risk evidence lane: current `M06 Residual Event Governance` owns missed-event checks, residual event intervention, attribution, and future event-family packet eligibility. It does not emit standalone directional-alpha event families.
- Event-family replay overlay gate: the 2026-06-10 sample impact-window run remains a contract verifier only. The all-family real-input follow-up calibrates 31 fold-visible/active families under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_real_input_backtest_20260610/`. The closed-loop all-family replay applies calibrated windows to `fold_2016-01_2016-06` / `model_group_replay_20260609T060059Z` under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_replay_20260610/`. These are fold-scoped event-governance evidence artifacts, not production promotion approval.
- Fold1 event-governance gate matrix: `/root/projects/trading-storage/storage/03_model_artifacts/layer_10_fold_completion_20260610/fold_2016-01_2016-06/model_group_replay_20260609T060059Z/` completes the fold-scoped evidence audit for 31 families. It marks fold1 evidence complete, production-route review complete, 31 calibrated overlay families, 0 diagnostic keyword-overlay families, 30 temporal-attention focus-pool admissions, and 1 current-definition rejection. Cross-fold stability is now follow-up monitoring for focus-pool families, not a prerequisite that blocks focus-pool entry.
- Realtime decision handoff remains parked until at least one model has an approved/promotable version.

The six model contracts have accepted boundaries and learning roles; see `docs/03_contracts.md` and `docs/23_model_learning_design.md`. The next work is implementation migration, objective-contract completion, historical evidence production, gate repair, calibration/baseline/stability/leakage evidence, and manager-side promotion review preparation.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- M01 and M02 require remediated real-data evidence before any promotion approval can be considered.
- M03-M06 require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review` requests.
- Missing evidence or failed gates must remain deferred/rejected and must not create runtime activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current promote-first historical-training run and must not be treated as active repository work items:

- realtime data/monitoring or live/shadow integration expansion before a model has an approved/promotable version;
- broker/order/fill/account lifecycle;
- production model activation without approved evaluation readiness and execution-owned runtime lifecycle gates;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Current Accepted Details

- Repository model-stack acceptance is complete for the current architecture boundary: six model contracts with accepted architecture/contracts, learning roles, docs, and canonical package homes.
- Retired ten-layer implementation packages are migration-source surfaces only, not current model contracts.
- M02 owns anonymous target candidate construction and model-facing target-state construction. Model-facing target context/state vectors must exclude ticker/company identity.
- M03 consumes accepted event-family contracts as frozen inputs. Event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, demotion/split/reweight/parameter revision, and future packet eligibility remain event-governance responsibilities.
- M04 owns adjusted after-cost edge, risk policy, exposure projection, and direct-underlying action as one current model contract with structured heads.
- Promotion acceptance evidence is recorded in `docs/31_promotion_acceptance.md`. No production activation occurred; promotion readiness belongs in `trading-evaluation`, and runtime activation belongs in `trading-execution`.
- Production-promotion readiness rules are accepted in `docs/30_promotion_readiness.md`: every production approval requires dataset snapshot, split, labels, evaluation run, metrics, candidate, thresholds, baselines, stability, leakage, calibration, and decision evidence.
- `docs/21_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Promotion review scripts emit model-side evidence/review artifacts only and may classify artifact retention intent. Promotion requests are manager-scheduled, readiness decisions are evaluation-owned, runtime activation/rollback pointers are execution-owned, and storage physical lifecycle execution remains `trading-storage`-owned.
- `docs/32_model_output_quality.md` owns the table-quality policy for keeping empty support payloads and nested explanation/diagnostic payloads out of primary model tables.

# Tasks

This is the active model task ledger. Keep it operational and tied to current gates. Detailed event-family evidence lives in `docs/51_event_family_scouting.md`, `docs/53_event_layer_final_judgment.md`, and the referenced storage artifacts.

## Active Tasks

- Production-promotion evidence lane: if continuing the current physical `model_01_*` through `model_10_*` surfaces, start with Layer 1 `MarketRegimeModel` promotion-gate repair/evidence production because Layer 2 and Layer 3 depend on a stable approved Layer 1 foundation. Use `scripts/models/model_01_market_regime/diagnose_model_01_market_regime_substrate.py` before any reviewed regeneration plan to separate source-bar sparsity, feature coverage/lookback gaps, and model-output alignment gaps.
- Six-training-block migration lane: the accepted training topology is now `M01-M02`, `M03`, `M04`, `M05-M08`, `M09`, and `M10` while preserving all ten runtime-facing contracts. The first architecture pilot should target `M05-M08` as a unified decision model with structured alpha/risk/position/action heads; do not delete target-selection, event-state, option-expression, or residual-event-governance contracts.
- Layer learning redesign: use `docs/23_model_learning_design.md` as the active route for model expansion. Before changing a layer implementation, write or verify its objective contract: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, walk-forward metric, leakage test, and downstream consumer.
- Model-output table quality gate: `scripts/models/audit_model_output_tables.py` audits all ten primary output tables plus `_explainability` and `_diagnostics` support tables for empty/sparse columns. `scripts/models/run_model_output_quality_gate.py` converts the audit into a post-generation pass/block result. Both paths are read-only; they do not drop columns or rewrite model rows.
- Event-risk evidence lane: keep Layer 10 bounded as `EventRiskGovernor / EventIntelligenceOverlay`. Current evidence accepts `cpi_inflation_release` and `earnings_guidance_scheduled_shell` as risk/control candidates only, accepts zero standalone directional-alpha event families, and leaves remaining families blocked/deferred/research-queue until reviewed gates are satisfied.
- Layer 10 completion gate: do not call Layer 10 evidence complete until the regular event-family workflow is complete for the active family universe: event-family packets, canonical parser/source routing, matched controls, impact-window backtests, fold stability, and leakage/upstream-overlap review. Architecture acceptance and closed-loop sample/replay artifacts are not enough.
- Event-family replay overlay gate: the 2026-06-10 sample impact-window run remains a contract verifier only. The all-family real-input follow-up calibrates 31 fold-visible/active families under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_real_input_backtest_20260610/`. The closed-loop all-family replay applies calibrated windows to `fold_2016-01_2016-06` / `model_group_replay_20260609T060059Z` under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_replay_20260610/`. These are fold-scoped Layer 10 evidence artifacts, not production promotion approval.
- Fold1 Layer 10 gate matrix: `/root/projects/trading-storage/storage/03_model_artifacts/layer_10_fold_completion_20260610/fold_2016-01_2016-06/model_group_replay_20260609T060059Z/` completes the fold-scoped evidence audit for 31 families. It marks fold1 evidence complete, production-route review complete, 31 calibrated overlay families, 0 diagnostic keyword-overlay families, 30 temporal-attention focus-pool admissions, and 1 current-definition rejection. Cross-fold stability is now follow-up monitoring for focus-pool families, not a prerequisite that blocks focus-pool entry.
- Realtime decision handoff remains parked until at least one model has an approved/promotable version.

The six training blocks and ten runtime contracts have accepted boundaries and learning roles; see `docs/03_contracts.md` and `docs/23_model_learning_design.md`. The next work is objective-contract completion, historical evidence production, gate repair, calibration/baseline/stability/leakage evidence, and manager-side promotion review preparation, not realtime integration expansion or ad hoc repository cleanup.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- Layer 1 and Layer 2 require remediated real-data evidence before any promotion approval can be considered.
- Layer 3 requires upstream Layer 1/2 production approval or an explicitly reviewed offline-evidence exception, plus Layer 3 calibration evidence.
- Layers 4-10 require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review` requests.
- Missing evidence or failed gates must remain deferred/rejected and must not create runtime activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current promote-first historical-training run and must not be treated as active repository work items:

- realtime data/monitoring or live/shadow integration expansion before a model has an approved/promotable version;
- broker/order/fill/account lifecycle;
- production model activation without approved evaluation readiness and execution-owned runtime lifecycle gates;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Current Accepted Details

- Repository model-stack acceptance is complete for the current architecture boundary: six training blocks preserve ten runtime contracts with accepted architecture/contracts, learning roles, docs, evaluation helpers where in scope, registry score naming, and fixture evidence.
- Layer 1 `MarketRegimeModel`, Layer 2 `SectorContextModel`, and Layer 3 `TargetStateVectorModel` have reviewed contracts, local baseline implementations/evaluation helpers, docs, and registry core-score naming. Production promotion remains deferred until real-sample gates pass.
- Layer 3 owns anonymous target candidate construction and model-facing target state-vector construction. Model-facing target context/state vectors must exclude ticker/company identity.
- Layer 4 `EventFailureRiskModel`, Layer 5 `AlphaConfidenceModel`, Layer 6 `DynamicRiskPolicyModel`, Layer 7 `PositionProjectionModel`, Layer 8 `UnderlyingActionModel`, Layer 9 `TradingGuidanceModel / OptionExpressionModel`, and Layer 10 `EventRiskGovernor / EventIntelligenceOverlay` have accepted offline model boundaries and learning roles.
- Promotion acceptance evidence is recorded in `docs/31_promotion_acceptance.md`: Layers 1-2 have real database evidence; Layers 3-10 have blocked/deferred evaluation evidence proving no production evaluation substrate exists yet. No production activation occurred; promotion readiness belongs in `trading-evaluation`, and runtime activation belongs in `trading-execution`.
- Production-promotion readiness rules are accepted for Layers 1-10 in `docs/30_promotion_readiness.md`: every production approval requires dataset snapshot, split, labels, evaluation run, metrics, candidate, thresholds, baselines, stability, leakage, calibration, and decision evidence.
- `docs/21_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Promotion review scripts emit model-side evidence/review artifacts only and may classify artifact retention intent. Promotion requests are manager-scheduled, readiness decisions are evaluation-owned, runtime activation/rollback pointers are execution-owned, and storage physical lifecycle execution remains `trading-storage`-owned.
- `docs/32_model_output_quality.md` owns the table-quality policy for keeping empty support payloads and nested explanation/diagnostic payloads out of primary model tables.

# Tasks

This is the active model task ledger. Keep it operational and tied to current gates. Detailed event-family evidence lives in `docs/51_event_family_scouting.md`, `docs/53_event_state_final_judgment.md`, and the referenced storage artifacts.

## Active Tasks

- Six-model implementation lane: deterministic current pilots are present for `M01 Background Context`, `M02 Target State`, `M03 Event State`, `M04 Unified Decision`, `M05 Option Expression`, and `M06 Residual Event Governance`. Current work targets these six model contracts directly.
- Current chain runner: `scripts/models/run_current_model_chain.py` executes the M01-M06 deterministic fixture route, emits `current_model_chain_receipt`, verifies handoff refs, label-leakage checks, and retired-field absence, and always keeps activation/promotion disallowed.
- Historical current-chain evidence runner: `scripts/models/run_current_model_historical_evaluation.py` reads bounded point-in-time historical rows, constructs current M01-M06 payloads, builds chronological monthly folds, joins mature future-return labels, and may train a local current-chain utility baseline artifact. It is read-only evidence generation; it never writes SQL, promotes, activates, or touches broker/account state.
- M01-M03 implementation pilots: deterministic background-context, target-state, and event-state generation/evaluation/review scripts are present under `scripts/models/model_01_background_context/`, `scripts/models/model_02_target_state/`, and `scripts/models/model_03_event_state/`. Remaining work is real point-in-time dataset assembly, labels, baselines, stability/leakage/calibration evidence, and promotion packages.
- M04 implementation pilot: deterministic `UnifiedDecisionModel` generation is present under `src/models/model_04_unified_decision/` with a current script at `scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py`. Remaining M04 work is real point-in-time dataset assembly, direct utility labels, walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and promotion evidence.
- M05 implementation pilot: deterministic `OptionExpressionModel` generation is present under `src/models/model_05_option_expression/` with current generate/evaluate/review scripts under `scripts/models/model_05_option_expression/`. It consumes current M04 `direct_underlying_intent`; remaining M05 work is option-chain replay labels, cost/fill/theta/IV validation, baseline evidence, leakage checks, calibration, and promotion evidence.
- M06 implementation pilot: deterministic `ResidualEventGovernanceModel` generation is present under `src/models/model_06_residual_event_governance/` with current generate/evaluate/review scripts under `scripts/models/model_06_residual_event_governance/`. It consumes current M04 `unified_decision_vector_ref` and optional M05 `option_expression_plan_ref`; remaining M06 work is real residual-event dataset assembly, intervention labels, overblock/accounting metrics, leakage checks, calibration, and promotion evidence.
- Model learning redesign: use `docs/23_model_learning_design.md` as the active route for model expansion. Before changing a model implementation, write or verify its objective contract: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, walk-forward metric, leakage test, and downstream consumer.
- Full-minute training coverage: historical training/evaluation should preserve every eligible minute as point-in-time state coverage, including no-event, no-action, no-option, and no-intervention rows. Live component invocation remains separate and may be gated by M04 or applicability checks.
- Model framework readiness: use `docs/24_model_framework_readiness.md` as the active rule for choosing model classes. PyTorch/deep learning is not a default dependency; it requires explicit neural-readiness evidence after strong non-deep baselines.
- Model-output table quality gate: `scripts/models/audit_model_output_tables.py` remains read-only and inspects current model output/support table families. `scripts/models/run_model_output_quality_gate.py` converts that audit into a pass/block decision for post-generation acceptance. Both paths are read-only; they do not drop columns or rewrite model rows.
- Event-risk evidence lane: current `M06 Residual Event Governance` owns missed-event checks, residual event intervention, attribution, and future event-family packet eligibility. It does not emit standalone directional-alpha event families.
- Event-family replay overlay gate: the 2026-06-10 sample impact-window run remains a contract verifier only. The all-family real-input follow-up calibrates 31 fold-visible/active families under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_real_input_backtest_20260610/`. The closed-loop all-family replay applies calibrated windows to `fold_2016-01_2016-06` / `model_group_replay_20260609T060059Z` under `/root/projects/trading-storage/storage/03_model_artifacts/event_family_impact_window_all_family_replay_20260610/`. These are fold-scoped event-governance evidence artifacts, not production promotion approval.
- Fold1 event-governance gate matrix: `/root/projects/trading-storage/storage/03_model_artifacts/m06_residual_event_governance_fold_completion_20260610/fold_2016-01_2016-06/model_group_replay_20260609T060059Z/` completes the fold-scoped evidence audit for 31 families. It marks fold1 evidence complete, production-route review complete, 31 calibrated overlay families, 0 diagnostic keyword-overlay families, 30 temporal-attention focus-pool admissions, and 1 current-definition rejection. Cross-fold stability is now follow-up monitoring for focus-pool families, not a prerequisite that blocks focus-pool entry.
- Realtime decision handoff remains parked until at least one model has an approved/promotable version.

The six model contracts have accepted boundaries, learning roles, and deterministic current pilots; see `docs/03_contracts.md` and `docs/23_model_learning_design.md`. The next work is objective-contract completion, historical evidence production, gate repair, calibration/baseline/stability/leakage evidence, and manager-side promotion review preparation.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- The current chain runner is a local contract smoke gate only. M01-M06 still require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review` requests before any promotion approval can be considered.
- The historical current-chain evidence runner is the first real historical evidence entrypoint. Passing it proves historical data can feed the current six-model chain and a baseline training/evaluation artifact; it does not prove model-specific promotion readiness by itself.
- The 2017Q1 historical current-chain pass over 750 point-in-time rows produced three monthly folds and full 1W label coverage, but all resolved actions were `no_trade`, all option expressions were `no_option_expression`, and all residual interventions were `no_intervention`. That is a valid mechanics receipt with degenerate decision distributions, not proof of tradable model behavior.
- Missing evidence or failed gates must remain deferred/rejected and must not create runtime activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current promote-first historical-training run and must not be treated as active repository work items:

- realtime data/monitoring or live/shadow integration expansion before a model has an approved/promotable version;
- broker/order/fill/account lifecycle;
- production model activation without approved evaluation readiness and execution-owned runtime lifecycle gates;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Current Accepted Details

- Repository model-stack acceptance is complete for the current architecture boundary: six model contracts with accepted architecture/contracts, learning roles, docs, canonical package homes, and deterministic local pilots.
- Historical retired serial implementation packages are not current model contracts.
- M02 owns anonymous target candidate construction and model-facing target-state construction. Model-facing target context/state vectors must exclude ticker/company identity.
- M03 consumes accepted event-family contracts as frozen inputs. Event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, demotion/split/reweight/parameter revision, and future packet eligibility remain event-governance responsibilities.
- M04 owns adjusted after-cost edge, risk policy, exposure projection, and direct-underlying action as one current model contract with structured heads.
- M06 owns current residual event-risk intervention after M04/M05 thesis formation. It must not emit retired `event_context_vector` or `underlying_action_plan` outputs.
- Promotion acceptance evidence is recorded in `docs/31_promotion_acceptance.md`. No production activation occurred; promotion readiness belongs in `trading-evaluation`, and runtime activation belongs in `trading-execution`.
- Production-promotion readiness rules are accepted in `docs/30_promotion_readiness.md`: every production approval requires dataset snapshot, split, labels, evaluation run, metrics, candidate, thresholds, baselines, stability, leakage, calibration, and decision evidence.
- `docs/21_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Promotion review scripts emit model-side evidence/review artifacts only and may classify artifact retention intent. Promotion requests are manager-scheduled, readiness decisions are evaluation-owned, runtime activation/rollback pointers are execution-owned, and storage physical lifecycle execution remains `trading-storage`-owned.
- `docs/32_model_output_quality.md` owns the table-quality policy for keeping empty support payloads and nested explanation/diagnostic payloads out of primary model tables.

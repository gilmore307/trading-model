# Tasks

This is the active model task ledger. Keep it operational and tied to current gates. Detailed event-family evidence lives in `docs/51_event_family_scouting.md`, `docs/53_event_state_final_judgment.md`, and the referenced storage artifacts.

## Active Tasks

- M01-M05 probability implementation lane: deterministic current pilots are present for `M01 Background Context`, `M02 Target State`, `M03 Event State`, `M04 Unified Decision`, and `M05 Option Expression`.
- Current chain runner: `scripts/models/run_current_model_chain.py` executes the M01-M05 deterministic fixture route, emits `current_model_chain_receipt`, verifies handoff refs, label-leakage checks, and retired-field absence, and always keeps activation/promotion disallowed.
- Historical current-chain evidence runner: `scripts/models/run_current_model_historical_evaluation.py` reads bounded point-in-time historical rows using liquidity-ranked, daily-stratified candidate sampling, constructs current M01-M05 payloads, builds chronological monthly folds, joins mature future-return labels, and may train a local cumulative residual-MLP utility baseline artifact for the chain-level evidence receipt. It blocks evaluation validity when the sample has only one target candidate or routing symbol, because single-target evidence is only a mechanics smoke path. It is read-only evidence generation; it never writes SQL, promotes, activates, or touches broker/account state.
- M01-M03 implementation pilots: deterministic background-context, target-state, and event-state generation/evaluation/review scripts are present under `scripts/models/model_01_background_context/`, `scripts/models/model_02_target_state/`, and `scripts/models/model_03_event_state/`. Remaining work is real point-in-time dataset assembly, labels, baselines, stability/leakage/calibration evidence, and promotion packages.
- M04 implementation pilot: deterministic `UnifiedDecisionModel` generation is present under `src/models/model_04_unified_decision/` with a current script at `scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py`. The historical current-chain replay now emits non-degenerate `open_long` / `open_short` / `no_trade` decisions from existing point-in-time target-state evidence. Remaining M04 work is promotion evidence: direct utility labels, broader walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and stability gates.
- M05 implementation pilot: deterministic `OptionExpressionModel` generation is present under `src/models/model_05_option_expression/` with current generate/evaluate/review scripts under `scripts/models/model_05_option_expression/`. It consumes the current M04 thesis surface and `direct_underlying_intent`, emits `expression_probability_surface`, then derives concrete `long_call` / `long_put` / underlying-only / no-option rows when point-in-time option candidates pass contract filters. Remaining M05 work is promotion evidence: option-expression labels, cost/fill/theta/IV validation, baselines, leakage checks, and calibration.
- Replay mechanism repair TODO: the first completed fold shows weak but nonzero ranking signal while M05/M04 mechanics remain structurally unsafe. Prioritize stronger no-trade gates, non-singleton option-expression selection, real expression diversity beyond dominant long calls, high-score-loss calibration, and short-DTE/tail-risk controls before treating more replay data as sufficient promotion evidence.
- M03 event-governance tooling: deterministic event-family taxonomy, modelability, impact-window, and packet-evidence helpers live under `src/models/model_03_event_state/event_governance/` with scripts under `scripts/models/model_03_event_state/event_governance/`. They provide evidence for M03 `event_effect_model` work and are not a separate model layer.
- Model learning redesign: use `docs/23_model_learning_design.md` as the active route for model expansion. Before changing a model implementation, write or verify its objective contract: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, walk-forward metric, leakage test, and downstream consumer.
- Full-minute training coverage: historical training/evaluation should preserve every eligible minute as point-in-time state coverage, including no-event, no-action, structural no-option, temporary option-chain-missing, and no-event absorption rows. Live component invocation remains separate and may be gated by M04 or applicability checks.
- Model framework readiness: use `docs/24_model_framework_readiness.md` as the active rule for learned schemes. The current accepted schemes are CPU-friendly GRU for M01/M03 and residual MLP for M02/M04/M05; every probability layer still needs layer-specific labels, replay, leakage, calibration, rollback, and promotion evidence before activation.
- Tradable-time return distribution surface: `src/models/return_distribution_surface/`, `scripts/models/build_tradable_time_return_distribution_surface.py`, and `scripts/models/build_tradable_time_return_distribution_surface_bundle.py` own the current read-only label/surface route for `tradable_time_return_distribution_surface`. The accepted shape is a single shape-constrained quantile/CDF surface over equal-step tradable-time target rows, with session-gap/open/close context inside the same function. This is not a skew-normal or fixed Gaussian family. The bundle route builds symbol/window surface artifacts, writes `surface_bundle_manifest.json`, and can run M04/M05 current-chain handoff smoke for each ready summary. Remaining work is to train/evaluate M01-M05 against walk-forward optionable-target surface bundles instead of scalar scores.
- Model-output table quality gate: `scripts/models/audit_model_output_tables.py` remains read-only and inspects current model output/support table families. `scripts/models/run_model_output_quality_gate.py` converts that audit into a pass/block decision for post-generation acceptance. Both paths are read-only; they do not drop columns or rewrite model rows.
- Current-chain surface closure gate: `scripts/models/run_current_model_chain.py --return-surface-summary-json <surface_summary.json>` verifies that a scoped surface summary can enter M04, that M04 records it in `thesis_distribution_surface`, and that M05 receives a matching thesis surface summary in `expression_candidate_set`. The gate blocks symbol/scope mismatch and remains read-only fixture evidence only.
- Event-risk evidence lane: M03 event-governance tooling owns missed-event checks, residual attribution, and future event-family packet eligibility only as evidence for M03 taxonomy/effect-model contracts. It does not emit standalone directional-alpha event families, component-control actions, or another probability layer.
- Event-family replay overlay gate: dated impact-window and fold-completion artifacts remain historical contract evidence only. Current event impact analysis belongs in the replay-review read models and the Events/Temporary Exploring dashboard surface, not in fold-specific manual replay paths.
- Realtime decision handoff remains parked until at least one model has an approved/promotable version.

The M01-M05 probability contracts have accepted boundaries, learning roles, deterministic current pilots, selected cumulative learned schemes, and a read-only historical current-chain replay route that can train a local cumulative residual-MLP utility artifact without provider, broker, activation, or SQL mutation. The next work is promotion evidence only: broader existing-data replay, calibration/baseline/stability/leakage evidence, M03 event-effect-model evidence, and manager-side promotion review preparation.

Latest return-surface closure smoke: an optionable-target bundle over `AAPL`,
`MSFT`, and `NVDA` for `2016-01` from
`trading_data.model_03_target_state_vector_data_acquisition` produced three
ready surfaces, each with zero CDF monotonicity failures and zero quantile
crossing repairs. Label rows were `79,794` per symbol; mean coverage error was
about `0.0084` for AAPL, `0.0065` for MSFT, and `0.0065` for NVDA. The local
M04/M05 current-chain surface handoff smoke passed for all three summaries.
No provider call, broker/account mutation, SQL mutation, storage-source
mutation, or model activation occurred.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- The current chain runner is a local contract smoke gate only. M01-M05 still require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review` requests before any promotion approval can be considered.
- The historical current-chain evidence runner is the first real historical evidence entrypoint. Passing it proves historical data can feed the current M01-M05 probability chain and a local cumulative residual-MLP utility training/evaluation artifact; it does not prove model-specific promotion readiness by itself.
- The old 2017Q1 degenerate-distribution limitation is superseded for the current implementation. The current historical replay path includes target-return direction normalization, point-in-time option candidates, standardized event interpretations, horizon selection from available evidence, and receipt fields for input coverage. A passing replay can now produce non-degenerate M04 actions and M05 option expressions while keeping activation and production promotion disabled.
- Latest existing-data retraining replay: `current_chain_retrain_replay_20260622T0903_et` wrote `/root/projects/trading-storage/storage/03_model_artifacts/current_chain_retrain_replay_20260622T0903_et/current_model_historical_evaluation.json`. It used 2021Q1 existing point-in-time rows only, trained the local cumulative residual-MLP utility baseline artifact, produced 750 generated chain rows across three monthly folds, 19 unique routing symbols, 100% mature label coverage, and no warning reasons. It performed no provider calls, SQL mutation, broker/account mutation, activation, or production promotion.
- Missing evidence or failed gates must remain deferred/rejected and must not create runtime activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current promote-first historical-training run and must not be treated as active repository work items:

- realtime data/monitoring or live/shadow integration expansion before a model has an approved/promotable version;
- broker/order/fill/account lifecycle;
- production model activation without approved evaluation readiness and execution-owned runtime lifecycle gates;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Current Accepted Details

- Repository model-stack acceptance is complete for the current M01-M05 probability architecture boundary, with event-governance compatibility surfaces pending migration into M03-owned contracts.
- Historical retired serial implementation packages are not current model contracts.
- M02 owns anonymous target candidate construction and model-facing target-state construction. Model-facing target context/state vectors must exclude ticker/company identity.
- M03 consumes accepted event-family contracts as frozen inputs. Event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, demotion/split/reweight/parameter revision, and future packet eligibility remain event-governance responsibilities.
- M04 owns adjusted after-cost edge, risk policy, exposure projection, and direct-underlying action as one current model contract with structured heads.
- M03 event-governance tooling must not emit retired `event_context_vector`, `underlying_action_plan`, or component-control outputs, and must feed M03 event-state/effect-model evidence rather than a separate probability layer.
- Promotion acceptance evidence is recorded in `docs/31_promotion_acceptance.md`. No production activation occurred; promotion readiness belongs in `trading-evaluation`, and runtime activation belongs in `trading-execution`.
- Production-promotion readiness rules are accepted in `docs/30_promotion_readiness.md`: every production approval requires dataset snapshot, split, labels, evaluation run, metrics, candidate, thresholds, baselines, stability, leakage, calibration, and decision evidence.
- `docs/21_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Promotion review scripts emit model-side evidence/review artifacts only and may classify artifact retention intent. Promotion requests are manager-scheduled, readiness decisions are evaluation-owned, runtime activation/rollback pointers are execution-owned, and storage physical lifecycle execution remains `trading-storage`-owned.
- `docs/32_model_output_quality.md` owns the table-quality policy for keeping empty support payloads and nested explanation/diagnostic payloads out of primary model tables.

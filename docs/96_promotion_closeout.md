# Promotion Closeout Decisions

Status: accepted current production-promotion closeout receipt; no production activation
Date: 2026-05-08

## What was actually executed

The closeout pass moved promotion from a framework-only state into concrete current decisions for all Layers 1-8.

- Layers 1-2 used real read-only PostgreSQL evaluation evidence and persisted deferred decisions from the generated artifacts.
- Layers 3-8 had no production evaluation substrate for their accepted contracts, so `scripts/models/review_layers_03_08_promotion_closeout.py` persisted formal blocked/deferred evaluation runs, metrics, candidates, and agent-reviewed decisions instead of leaving them as undocumented gaps.
- No layer was approved and no production activation occurred.

| Layer | Model | Evidence source | Evaluation receipt | Decision receipt | Result | Activation |
|---:|---|---|---|---|---|---|
| 1 | `model_01_market_regime` | PostgreSQL read-only: regenerated `trading_data.feature_01_market_regime` + `trading_model.model_01_market_regime` | `mdevrun_1f36fd090ec5dc03` / `mdsnap_141ef99ca8da5875` | `mpdec_fb175b8c8a6b7bbf` for candidate `mpcand_5256bbfb6a02e85d` | deferred after repair: data completeness fixed, but baseline/coverage/stability still fail | none |
| 2 | `model_02_sector_context` | PostgreSQL read-only: regenerated `trading_data.feature_02_sector_context` + `trading_model.model_02_sector_context` | `mdevrun_696127b7faef4cac` / `mdsnap_04b65eabc7ed9410` | `mpdec_03cd8113817e7cd9` for candidate `mpcand_680b51bc7afb02bd` | deferred after repair: coverage passes, but baseline/lift gates still fail | none |
| 3 | `model_03_target_state_vector` | PostgreSQL production-eval substrate: `trading_data.feature_03_target_state_vector` + generated `trading_model.model_03_target_state_vector` | `mdevrun_327616bb447ceb5b` / `mdsnap_9b7c3bd598114c7c` | `mpdec_70fef0f31847cc1c` for candidate `mpcand_1b077bca49a18dbf` | deferred: real substrate present, but upstream L1/L2 approvals and calibration evidence missing | none |
| 4 | `model_04_event_overlay` | formal closeout blocker: missing production event-overlay eval run / calibrated labels | `mdevrun_closeout_l04_no_eval_substrate_20260508` / `mdsnap_closeout_l04_no_eval_substrate_20260508` | `mpdec_76b07ea01a3f525b` for candidate `mpcand_6ab73401f22ab057` | deferred: no production eval substrate | none |
| 5 | `model_05_alpha_confidence` | formal closeout blocker: missing production adjusted-alpha eval run / calibrated labels | `mdevrun_closeout_l05_no_eval_substrate_20260508` / `mdsnap_closeout_l05_no_eval_substrate_20260508` | `mpdec_9c3e19d6559ef55b` for candidate `mpcand_72289e5cc95ae2d5` | deferred: no production eval substrate | none |
| 6 | `model_06_position_projection` | formal closeout blocker: missing production position-utility eval run / labels | `mdevrun_closeout_l06_no_eval_substrate_20260508` / `mdsnap_closeout_l06_no_eval_substrate_20260508` | `mpdec_b118232e76fae092` for candidate `mpcand_622c6ffa9ffca030` | deferred: no production eval substrate | none |
| 7 | `model_07_underlying_action` | formal closeout blocker: missing production realized-action outcome eval run | `mdevrun_closeout_l07_no_eval_substrate_20260508` / `mdsnap_closeout_l07_no_eval_substrate_20260508` | `mpdec_fabc9c709149a698` for candidate `mpcand_d4911cef39a14b97` | deferred: no production eval substrate | none |
| 8 | `model_08_option_expression` | formal closeout blocker: missing production option-chain replay eval run | `mdevrun_closeout_l08_no_eval_substrate_20260508` / `mdsnap_closeout_l08_no_eval_substrate_20260508` | `mpdec_e7448aaab1334345` for candidate `mpcand_9de333239d5c3f12` | deferred: no production eval substrate | none |

This is the current honest closeout: every layer has a persisted current promotion disposition; none is production-approved.

## Layer 1 decision evidence

`model_01_market_regime` read real database rows and persisted the generated governance artifacts plus a deferred promotion decision. A follow-up repair regenerated the stale Layer 1 feature/model tables, raising the evaluation sample to `3275` feature rows, `3275` model rows, and `6472` labels. The stale row-count and leakage failures were removed, but the model still did not satisfy promotion gates.

Latest failing gates after repair:

- baseline improvement failed: `minimum_baseline_improvement_abs = -0.35178356856387916`, threshold `>= 0.0`;
- coverage failed: `minimum_coverage = 0.6497695852534562`, threshold `>= 0.8`;
- split sign stability failed: `minimum_stability_sign_consistency = 0.3333333333333333`, threshold `>= 0.66`.

Passing gates after repair included leakage (`0` violations), split count, feature/model row counts, label count, pair count, correlation range, and state-output absolute Pearson. The remaining failures are therefore treated as current evidence/behavior blockers, not as permission to lower thresholds.

Because the decision was deferred, no config activation was allowed or performed.

## Layer 2 decision evidence

`model_02_sector_context` read real database rows and persisted the generated governance artifacts plus a deferred promotion decision. A follow-up repair regenerated Layer 2 features/model rows after source-fetch and generator optimizations. The latest evaluation used `104800` feature rows, `81875` model rows, and `198322` labels.

Latest failing gates after repair:

- baseline improvement failed: `minimum_baseline_improvement_abs = -0.6002657404367061`, threshold `>= 0.0`;
- selected-vs-blocked lift failed: `minimum_selected_abs_label_lift_vs_blocked = -0.005092477576509518`, threshold `>= 0.0`;
- split sign stability failed: `minimum_stability_sign_consistency = 0.3333333333333333`, threshold `>= 0.66`.

Positive evidence existed for row counts, coverage (`0.8743002544529263` against `>= 0.8`), leakage, selected count, factor correlation, and handoff metrics, but the failed baseline/lift/stability gates still force deferral. Because the decision was deferred, no config activation was allowed or performed.

## Layer 3 follow-up production-eval substrate

Layer 3 is no longer merely blocked for a missing production-evaluation substrate. A follow-up run created the first real Layer 3 substrate from PostgreSQL-backed feature/model rows:

- source evidence: Alpaca-backed ETF target bars loaded through `trading-data`, normalized through `source_03_target_state`, and generated into `trading_data.feature_03_target_state_vector`;
- feature rows: `576`;
- generated model rows: `576` in `trading_model.model_03_target_state_vector`;
- evaluation labels: `1604` `future_target_tradeable_path` labels;
- snapshot: `mdsnap_9b7c3bd598114c7c`;
- eval run: `mdevrun_327616bb447ceb5b`;
- candidate: `mpcand_1b077bca49a18dbf`;
- reviewer-agent decision: `mpdec_70fef0f31847cc1c`, deferred.

The Layer 3 promotion thresholds passed on this substrate: feature/model row count, label count, split count, baseline ladder, target-vs-market and target-vs-market-sector improvement, split stability, and leakage checks. The reviewer still deferred promotion because:

- Layer 1 and Layer 2 are themselves deferred after real evaluation and are not production-approved/active upstream dependencies;
- calibration evidence for Layer 3 is missing;
- the proposed config `mcfg_582101fd83b5fbee` must not activate from a deferred decision.

The reproducible entrypoint for this follow-up is `scripts/models/model_03_target_state_vector/review_target_state_vector_production_substrate.py`.

## Layers 4-8 decision evidence

Layers 4-8 still have explicit persisted agent-reviewed closeout decisions rather than informal blockers. The script `scripts/models/review_layers_03_08_promotion_closeout.py` uses the same promotion-review principle as Layers 1-2: build evaluation artifacts, create a promotion candidate, call `openclaw agent` for the final review, persist the reviewed decision, and never activate a deferred/rejected candidate. Their evaluation runs intentionally record `run_status = blocked`, one `production_eval_run_available = 0` metric, and deferred decisions whose blockers are:

- production evaluation run missing;
- production labels missing;
- production metrics missing.

These rows are not synthetic approval evidence. They are durable negative/blocked evidence proving that the promotion route was evaluated and cannot proceed until the missing production substrate exists. Layer 4 requires real event-overlay labels; Layer 5 requires calibrated adjusted-alpha outcomes; Layer 6 requires position-utility/outcome labels; Layer 7 requires realized underlying-action outcomes; Layer 8 requires option-chain replay and option-expression outcome evidence.

## Activation invariant

No production config is active from this closeout pass. Deferred decisions must not create `model_promotion_activation` rows or move active config pointers.

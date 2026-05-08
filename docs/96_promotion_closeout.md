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
| 1 | `model_01_market_regime` | PostgreSQL read-only: `trading_data.feature_01_market_regime` + `trading_model.model_01_market_regime` | `mdevrun_1d00f2757982bd63` / `mdsnap_dc61e0e823ca4850` | `mpdec_d743cb5dbc8159f2` for candidate `mpcand_b79411e80a774787` | deferred | none |
| 2 | `model_02_sector_context` | PostgreSQL read-only: `trading_data.feature_02_sector_context` + `trading_model.model_02_sector_context` | `mdevrun_00c81e53569941df` / `mdsnap_fa3982c8d482017f` | `mpdec_3ab83ea1f423326d` for candidate `mpcand_a6044e72162553f9` | deferred | none |
| 3 | `model_03_target_state_vector` | PostgreSQL production-eval substrate: `trading_data.feature_03_target_state_vector` + generated `trading_model.model_03_target_state_vector` | `mdevrun_327616bb447ceb5b` / `mdsnap_9b7c3bd598114c7c` | `mpdec_70fef0f31847cc1c` for candidate `mpcand_1b077bca49a18dbf` | deferred: real substrate present, but upstream L1/L2 approvals and calibration evidence missing | none |
| 4 | `model_04_event_overlay` | formal closeout blocker: missing production event-overlay eval run / calibrated labels | `mdevrun_closeout_l04_no_eval_substrate_20260508` / `mdsnap_closeout_l04_no_eval_substrate_20260508` | `mpdec_76b07ea01a3f525b` for candidate `mpcand_6ab73401f22ab057` | deferred: no production eval substrate | none |
| 5 | `model_05_alpha_confidence` | formal closeout blocker: missing production adjusted-alpha eval run / calibrated labels | `mdevrun_closeout_l05_no_eval_substrate_20260508` / `mdsnap_closeout_l05_no_eval_substrate_20260508` | `mpdec_9c3e19d6559ef55b` for candidate `mpcand_72289e5cc95ae2d5` | deferred: no production eval substrate | none |
| 6 | `model_06_position_projection` | formal closeout blocker: missing production position-utility eval run / labels | `mdevrun_closeout_l06_no_eval_substrate_20260508` / `mdsnap_closeout_l06_no_eval_substrate_20260508` | `mpdec_b118232e76fae092` for candidate `mpcand_622c6ffa9ffca030` | deferred: no production eval substrate | none |
| 7 | `model_07_underlying_action` | formal closeout blocker: missing production realized-action outcome eval run | `mdevrun_closeout_l07_no_eval_substrate_20260508` / `mdsnap_closeout_l07_no_eval_substrate_20260508` | `mpdec_fabc9c709149a698` for candidate `mpcand_d4911cef39a14b97` | deferred: no production eval substrate | none |
| 8 | `model_08_option_expression` | formal closeout blocker: missing production option-chain replay eval run | `mdevrun_closeout_l08_no_eval_substrate_20260508` / `mdsnap_closeout_l08_no_eval_substrate_20260508` | `mpdec_e7448aaab1334345` for candidate `mpcand_9de333239d5c3f12` | deferred: no production eval substrate | none |

This is the current honest closeout: every layer has a persisted current promotion disposition; none is production-approved.

## Layer 1 decision evidence

`model_01_market_regime` read real database rows and persisted the generated governance artifacts plus a deferred promotion decision.

Key failing gates:

- baseline improvement failed: minimum observed `baseline_improvement_abs = -0.6660030004362388`, threshold `>= 0.0`;
- leakage/alignment failed: `total_leakage_violation_count = 6`, threshold `<= 0`;
- model row count failed: `130`, threshold `>= 252`;
- stability evidence was absent / failed: `minimum_stability_sign_consistency = 0.0`, threshold `>= 0.66`.

Because the decision was deferred, no config activation was allowed or performed.

## Layer 2 decision evidence

`model_02_sector_context` read real database rows and persisted the generated governance artifacts plus a deferred promotion decision.

Key failing gates:

- baseline improvement failed: minimum observed `baseline_improvement_abs = -0.29879136549850716`, threshold `>= 0.0`;
- split sign stability failed: minimum observed `split_stability_sign_consistency = 0.3333333333333333`, threshold `>= 0.66`.

Positive evidence existed for row counts, coverage, leakage, selected count, and handoff metrics, but the failed baseline/stability gates still force deferral. Because the decision was deferred, no config activation was allowed or performed.

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

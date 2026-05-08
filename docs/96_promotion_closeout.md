# Promotion Closeout Decisions

Status: accepted current production-promotion closeout receipt; no production activation
Date: 2026-05-08

## What was actually executed

The closeout pass moved promotion from a framework-only state into concrete current decisions for all Layers 1-8.

- Layers 1-2 used real read-only PostgreSQL evaluation evidence and persisted deferred decisions from the generated artifacts.
- Layers 3-8 had no production evaluation substrate for their accepted contracts, so the closeout persisted formal blocked/deferred evaluation runs, metrics, candidates, and decisions instead of leaving them as undocumented gaps.
- No layer was approved and no production activation occurred.

| Layer | Model | Evidence source | Evaluation receipt | Decision receipt | Result | Activation |
|---:|---|---|---|---|---|---|
| 1 | `model_01_market_regime` | PostgreSQL read-only: `trading_data.feature_01_market_regime` + `trading_model.model_01_market_regime` | `mdevrun_1d00f2757982bd63` / `mdsnap_dc61e0e823ca4850` | `mpdec_d743cb5dbc8159f2` for candidate `mpcand_b79411e80a774787` | deferred | none |
| 2 | `model_02_sector_context` | PostgreSQL read-only: `trading_data.feature_02_sector_context` + `trading_model.model_02_sector_context` | `mdevrun_00c81e53569941df` / `mdsnap_fa3982c8d482017f` | `mpdec_3ab83ea1f423326d` for candidate `mpcand_a6044e72162553f9` | deferred | none |
| 3 | `model_03_target_state_vector` | formal closeout blocker: missing production SQL evidence table / eval substrate | `mdevrun_closeout_l03_no_eval_substrate_20260508` / `mdsnap_closeout_l03_no_eval_substrate_20260508` | `mpdec_31899733788d324d` for candidate `mpcand_fffc92ba53b09199` | deferred: no production eval substrate | none |
| 4 | `model_04_event_overlay` | formal closeout blocker: missing production event-overlay eval run / calibrated labels | `mdevrun_closeout_l04_no_eval_substrate_20260508` / `mdsnap_closeout_l04_no_eval_substrate_20260508` | `mpdec_c118afa20c4e9bf2` for candidate `mpcand_6ab73401f22ab057` | deferred: no production eval substrate | none |
| 5 | `model_05_alpha_confidence` | formal closeout blocker: missing production adjusted-alpha eval run / calibrated labels | `mdevrun_closeout_l05_no_eval_substrate_20260508` / `mdsnap_closeout_l05_no_eval_substrate_20260508` | `mpdec_dc408c9914a4723a` for candidate `mpcand_72289e5cc95ae2d5` | deferred: no production eval substrate | none |
| 6 | `model_06_position_projection` | formal closeout blocker: missing production position-utility eval run / labels | `mdevrun_closeout_l06_no_eval_substrate_20260508` / `mdsnap_closeout_l06_no_eval_substrate_20260508` | `mpdec_7b9d7279fecfdf6a` for candidate `mpcand_622c6ffa9ffca030` | deferred: no production eval substrate | none |
| 7 | `model_07_underlying_action` | formal closeout blocker: missing production realized-action outcome eval run | `mdevrun_closeout_l07_no_eval_substrate_20260508` / `mdsnap_closeout_l07_no_eval_substrate_20260508` | `mpdec_5e6e83b02ccda12e` for candidate `mpcand_d4911cef39a14b97` | deferred: no production eval substrate | none |
| 8 | `model_08_option_expression` | formal closeout blocker: missing production option-chain replay eval run | `mdevrun_closeout_l08_no_eval_substrate_20260508` / `mdsnap_closeout_l08_no_eval_substrate_20260508` | `mpdec_90721592be6591c8` for candidate `mpcand_9de333239d5c3f12` | deferred: no production eval substrate | none |

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

## Layers 3-8 decision evidence

Layers 3-8 now have explicit persisted closeout decisions rather than informal blockers. Their evaluation runs intentionally record `run_status = blocked`, one `production_eval_run_available = 0` metric, and deferred decisions whose blockers are:

- production evaluation run missing;
- production labels missing;
- production metrics missing.

These rows are not synthetic approval evidence. They are durable negative/blocked evidence proving that the promotion route was evaluated and cannot proceed until the missing production substrate exists.

## Activation invariant

No production config is active from this closeout pass. Deferred decisions must not create `model_promotion_activation` rows or move active config pointers.

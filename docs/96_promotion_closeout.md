# Promotion Closeout Decisions

Status: accepted current production-promotion closeout receipt; no production activation
Date: 2026-05-08

## What was actually executed

The closeout pass moved promotion from a framework-only state into concrete current decisions where real database evidence exists.

| Layer | Model | Evidence source | Evaluation receipt | Decision receipt | Result | Activation |
|---:|---|---|---|---|---|---|
| 1 | `model_01_market_regime` | PostgreSQL read-only: `trading_data.feature_01_market_regime` + `trading_model.model_01_market_regime` | `mdevrun_1d00f2757982bd63` / `mdsnap_dc61e0e823ca4850` | `mpdec_d743cb5dbc8159f2` for candidate `mpcand_b79411e80a774787` | deferred | none |
| 2 | `model_02_sector_context` | PostgreSQL read-only: `trading_data.feature_02_sector_context` + `trading_model.model_02_sector_context` | `mdevrun_00c81e53569941df` / `mdsnap_fa3982c8d482017f` | `mpdec_3ab83ea1f423326d` for candidate `mpcand_a6044e72162553f9` | deferred | none |
| 3 | `model_03_target_state_vector` | no production SQL evidence table present for this closeout pass | none | none | blocked: no evaluable production evidence | none |
| 4 | `model_04_event_overlay` | no production evaluation run / calibrated labels present | none | none | blocked: no evaluable production evidence | none |
| 5 | `model_05_alpha_confidence` | no production evaluation run / calibrated labels present | none | none | blocked: no evaluable production evidence | none |
| 6 | `model_06_position_projection` | no production evaluation run / utility labels present | none | none | blocked: no evaluable production evidence | none |
| 7 | `model_07_underlying_action` | no production evaluation run / realized action outcomes present | none | none | blocked: no evaluable production evidence | none |
| 8 | `model_08_option_expression` | no production evaluation run / option replay outcomes present | none | none | blocked: no evaluable production evidence | none |

This is the current honest closeout: Layers 1-2 have persisted deferred decisions from real database evidence; Layers 3-8 are explicitly blocked because the evidence substrate does not exist yet.

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

## Layers 3-8 blocker classification

Layers 3-8 cannot be promoted or formally deferred through `model_promotion_decision` rows yet because no production evaluation run exists for their current contracts. Creating fake candidates would be worse than leaving the block explicit because the promotion schema requires an `eval_run_id` foreign key.

The required next work is not more wording. It is to create real point-in-time datasets, labels, evaluation runs, metrics, and candidates for each layer in dependency order, then run the same defer/approve gate.

## Activation invariant

No production config is active from this closeout pass. Deferred decisions must not create `model_promotion_activation` rows or move active config pointers.

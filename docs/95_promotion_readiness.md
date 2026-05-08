# Promotion Readiness

Status: accepted production-hardening gate contract; no production approval implied
Date: 2026-05-07

## Purpose

Layers 1-8 are structurally closed for model design, but production promotion is a separate evidence gate. This document turns the accepted promotion/calibration rules into a single per-layer readiness matrix and checklist.

A layer may not be treated as production-promoted merely because its contract, deterministic scaffold, fixture tests, registry score names, or local evaluation helpers exist.

## Required evidence package

Every model-layer production promotion candidate must be rooted in a complete evidence package:

```text
model_dataset_snapshot
  ├─ model_dataset_split
  ├─ model_eval_label
  └─ model_eval_run
        └─ model_promotion_metric
              └─ model_promotion_candidate
                    └─ model_promotion_decision
```

The review package must include at minimum:

| Evidence | Required purpose |
|---|---|
| `dataset_snapshot_ref` | frozen point-in-time input universe and extraction provenance |
| `dataset_split_ref` | chronological train/calibration/validation/test windows |
| `eval_label_refs` | label definitions by horizon and outcome family |
| `eval_run_ref` | immutable evaluation run that produced candidate evidence |
| `promotion_metric_refs` | metric rows tied to the evaluation run |
| `promotion_candidate_ref` | candidate config/model artifact being reviewed |
| `thresholds_ref` | reviewed thresholds for approval/defer/reject |
| `baseline_comparison_ref` | accepted baseline ladder results |
| `split_stability_ref` | split/rolling/expanding stability evidence |
| `leakage_check_ref` | no-future/no-identity/no-downstream leakage evidence |
| `calibration_report_ref` | threshold/scaler/probability/rank calibration evidence where applicable |
| `decision_record_ref` | human/agent review decision receipt |

Missing any required item means the review action is **defer**, not approve.

## Promotion readiness matrix

| Layer | Model | Output | Current production status | Blocking gap |
|---:|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_context_state` | deferred after real evaluation | persisted decision `mpdec_d743cb5dbc8159f2`; failed baseline, leakage/alignment, model-row-count, and stability gates |
| 2 | `SectorContextModel` | `sector_context_state` | deferred after real evaluation | persisted decision `mpdec_3ab83ea1f423326d`; failed baseline-improvement and split-stability gates |
| 3 | `TargetStateVectorModel` | `target_context_state` | deferred: no production eval substrate | persisted decision `mpdec_d8e027dd9b5aa939`; no production SQL evidence table / eval run exists for current contract |
| 4 | `EventOverlayModel` | `event_context_vector` | deferred: no production eval substrate | persisted decision `mpdec_76b07ea01a3f525b`; no production event-overlay evaluation run or calibrated labels exist |
| 5 | `AlphaConfidenceModel` | `alpha_confidence_vector` | deferred: no production eval substrate | persisted decision `mpdec_9c3e19d6559ef55b`; no production adjusted-alpha evaluation run or calibrated labels exist |
| 6 | `PositionProjectionModel` | `position_projection_vector` | deferred: no production eval substrate | persisted decision `mpdec_b118232e76fae092`; no production position-utility evaluation run or labels exist |
| 7 | `UnderlyingActionModel` | `underlying_action_plan` / `underlying_action_vector` | deferred: no production eval substrate | persisted decision `mpdec_fabc9c709149a698`; no production realized-action outcome evaluation run exists |
| 8 | `OptionExpressionModel` | `option_expression_plan` / `expression_vector` | deferred: no production eval substrate | persisted decision `mpdec_e7448aaab1334345`; no production option-chain replay evaluation run exists |

No layer in this matrix is currently production-approved by this document.

## Calibration gates

Calibration is required before production approval whenever a layer emits thresholds, probabilities, ranks, confidence scores, utility scores, eligibility scores, or resolved decisions.

Calibration evidence must state:

- calibration population and timestamp boundaries;
- label family and horizon;
- pre/post calibration metrics;
- monotonicity or rank-order checks where relevant;
- split stability and drift sensitivity;
- threshold sensitivity around approval boundaries;
- fallback/degrade behavior when calibration evidence is stale or missing.

## Baseline gates

Promotion candidates must beat the accepted baseline ladder for their layer. A layer-specific baseline ladder may be richer, but it may not omit the relevant lower-context or simpler-policy baselines already described in the layer contract.

If baseline improvement is not positive and stable on the reviewed split windows, promotion must be deferred even when fixture tests pass.

## Activation rule

An accepted approval decision may activate a config only through the promotion activation path. Deferred or rejected decisions must never activate or move production pointers.

The 2026-05-08 closeout pass persisted deferred decisions for Layers 1-8 and created no activation rows. Layers 3-8 were routed through `scripts/models/review_layers_03_08_promotion_closeout.py`, which calls the reviewer agent before persisting decisions. See `96_promotion_closeout.md` for the current decision receipts.

## Implementation hook

`src/model_governance/promotion/readiness.py` owns the lightweight reusable validation helper for this checklist. It verifies required evidence fields and gate results; it does not approve models by itself.

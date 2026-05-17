# Promotion Readiness
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-17): conceptual Layers 4-9 are now Layer 4 EventFailureRiskModel, Layer 5 AlphaConfidenceModel, Layer 6 PositionProjectionModel, Layer 7 UnderlyingActionModel, Layer 8 TradingGuidanceModel / OptionExpressionModel, and Layer 9 EventRiskGovernor / EventIntelligenceOverlay. Physical implementation paths for Layers 4-9 remain on prior numbering until a dedicated code/SQL renumbering migration.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: accepted production-hardening gate contract; no production approval implied
Date: 2026-05-07

## Purpose

Layers 1-9 are structurally revised for model design, but production promotion is a separate evidence gate. This document turns the accepted promotion/calibration rules into a single per-layer readiness matrix and checklist.

A layer may not be treated as production-promoted merely because its contract, deterministic scaffold, fixture tests, registry score names, or local evaluation helpers exist.

## Required evidence package

Every model-layer production promotion candidate must be rooted in a complete evidence package:

```text
model_dataset_snapshot
  ├─ model_dataset_split
  ├─ model_eval_label
  └─ model_eval_run
        └─ model_promotion_metric
              └─ promotion_candidate_evidence
                    └─ model_promotion_review in trading-manager
                          └─ review_decision
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

## Realtime validation boundary

Realtime data is an accepted forward evidence source only after it is captured as point-in-time shadow/forward-validation data with frozen model/config refs and mature labels. It is not a shortcut around the chronological historical split ladder.

Promotion reviews should distinguish:

1. historical broad-sample validation/test evidence;
2. historical live-route simulation evidence;
3. realtime shadow or forward-holdout evidence collected after the model/config was frozen.

Realtime evidence becomes stronger as it accumulates untouched future rows, but early realtime windows are usually too short and label-delayed to prove baseline lift, split stability, calibration, and leakage safety by themselves. A candidate that lacks historical validation/test evidence must be deferred even if realtime capture is structurally connected.

## Promotion readiness matrix

| Layer | Model | Output | Current production status | Blocking gap |
|---:|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_context_state` | deferred after real evaluation | failed baseline, eval-label count, pair-count, and coverage gates; split-stability and leakage currently pass |
| 2 | `SectorContextModel` | `sector_context_state` | deferred after real evaluation | failed baseline/lift and split-stability gates |
| 3 | `TargetStateVectorModel` | `target_context_state` | deferred after real production-eval substrate | upstream Layer 1/2 are not production-approved/active and Layer 3 calibration evidence is missing |
| 4 | `EventFailureRiskModel` | `event_failure_risk_vector` | deferred: no production eval substrate | no accepted production implementation/evaluation run for reviewed event/strategy-failure conditioning exists |
| 5 | `AlphaConfidenceModel` | `alpha_confidence_vector` | deferred: no production eval substrate | no production adjusted-alpha evaluation run or calibrated labels exist |
| 6 | `PositionProjectionModel` | `position_projection_vector` | deferred: no production eval substrate | no production position-utility evaluation run or labels exist |
| 7 | `UnderlyingActionModel` | `underlying_action_plan` / `underlying_action_vector` | deferred: no production eval substrate | no production realized-action outcome evaluation run exists |
| 8 | `OptionExpressionModel` | `option_expression_plan` / `expression_vector` | deferred: no production eval substrate | no production option-chain replay evaluation run exists |
| 9 | `EventRiskGovernor` | `event_context_vector` / `event_risk_intervention` | deferred: no production eval substrate | no production residual-event-governor evaluation run or calibrated labels exist |

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

An accepted approval may activate a config only through `trading-manager` manager-control-plane review and activation. Deferred or rejected reviews must never activate or move production pointers.

Promotion evidence and activation helpers may classify artifact retention intent, but they must not call cleanup, compression, archive, SQL detach/drop, or deletion executors directly. The accepted boundary is:

```text
promotion classifies artifacts
manager schedules lifecycle
storage executes lifecycle
```

Approved/promoted model bodies and required lineage must be marked for permanent retention. Regenerable intermediates may receive retention hints, but lifecycle action must route through manager `storage_lifecycle_request` and storage protected-set execution.

The current closeout evidence creates no activation rows. Layers 3-8 route through `scripts/models/review_layers_03_08_promotion_closeout.py`, which builds blocked evidence and reviewer artifacts without persisting manager decisions. A follow-up Layer 3 substrate run can rebuild real Layer 3 evaluation evidence, but Layers 4-9 remain blocked for missing production eval substrate. See `96_promotion_closeout.md` for the current evidence receipt.

## Implementation hook

`src/model_governance/promotion/readiness.py` owns the lightweight reusable validation helper for this checklist. It verifies required evidence fields and gate results; it does not approve models by itself.

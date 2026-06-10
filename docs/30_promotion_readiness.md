# Promotion Readiness

Status: accepted production-hardening gate contract; no production approval implied
Date: 2026-06-10

## Purpose

The six current model contracts have accepted model-design boundaries, but production promotion is a separate evidence gate. This document turns the accepted promotion/calibration rules into a single per-model readiness matrix and checklist.

A model may not be treated as production-promoted merely because its contract, baseline generator, fixture tests, registry score names, or local evaluation helpers exist.

## Required Evidence Package

Every model production promotion candidate must be rooted in a complete evidence package:

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

Missing any required dataset, split, label, evaluation, metric, candidate, threshold, baseline, stability, leakage, calibration, or review item means the review action is **defer**, not approve.

## Realtime Validation Boundary

Realtime data is an accepted forward evidence source only after it is captured as point-in-time shadow/forward-validation data with frozen model/config refs and mature labels. It is not a shortcut around the chronological historical split ladder.

Promotion reviews should distinguish:

1. historical broad-sample validation/test evidence;
2. historical live-route simulation evidence;
3. realtime shadow or forward-holdout evidence collected after the model/config was frozen.

## Promotion Readiness Matrix

| Model | Output | Current production status | Blocking gap |
|---|---|---|---|
| `M01 BackgroundContextModel` | `background_context_state` | deferred: migration/evaluation required | current six-model implementation and real evaluation evidence missing |
| `M02 TargetStateModel` | `target_context_state` | deferred: migration/evaluation required | six-model target-state implementation, upstream M01 evidence, and calibration evidence missing |
| `M03 EventStateModel` | `event_state_vector` | deferred: migration/evaluation required | six-model event-state implementation, accepted event-family inputs, and calibrated labels missing |
| `M04 UnifiedDecisionModel` | `unified_decision_vector` | deferred: deterministic pilot only | unified decision training/evaluation run, direct utility labels, and replay evidence missing |
| `M05 OptionExpressionModel` | `option_expression_plan` / `expression_vector` | deferred: deterministic pilot only | option-chain replay labels, cost/fill/theta/IV validation, and baseline evidence missing |
| `M06 ResidualEventGovernanceModel` | `event_risk_intervention` / packet eligibility | deferred: migration/evaluation required | residual event-governance evaluation run and calibrated residual-risk labels missing |

No model in this matrix is currently production-approved by this document.

## Calibration Gates

Calibration is required before production approval whenever a model emits thresholds, probabilities, ranks, confidence scores, utility scores, eligibility scores, or resolved decisions.

## Baseline Gates

Promotion candidates must beat the accepted baseline ladder for their model. A model-specific baseline ladder may be richer, but it may not omit the relevant lower-context or simpler-policy baselines already described in the model contract.

If baseline improvement is not positive and stable on the reviewed split windows, promotion must be deferred even when fixture tests pass.

## Activation Rule

An accepted approval may admit a model only into the evaluation-owned promotion-readiness and execution-owned runtime lifecycle path. Deferred or rejected reviews must never activate or move production pointers.

Promotion evidence and activation helpers may classify artifact retention intent, but they must not call cleanup, compression, archive, SQL detach/drop, or deletion executors directly. The accepted boundary is:

```text
promotion classifies artifacts
manager schedules lifecycle
storage executes lifecycle
```

Approved/promoted model bodies and required lineage must be marked for permanent retention. Regenerable intermediates may receive retention hints, but lifecycle action must route through manager `storage_lifecycle_request` and storage protected-set execution.

Current retained promotion helpers that reference the retired ten-layer route are migration-source helpers only. New promotion readiness evidence should target the six current model contracts.

## Implementation Hook

`src/model_governance/promotion/readiness.py` owns the lightweight reusable validation helper for this checklist. It verifies required evidence fields and gate results; it does not approve models by itself.

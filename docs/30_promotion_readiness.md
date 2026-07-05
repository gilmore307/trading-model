# Promotion Readiness

Status: accepted production-hardening gate contract; no production approval implied
Date: 2026-06-10

## Purpose

The six current model contracts have accepted model-design boundaries and active learned scheme selections, but production promotion is a separate evidence gate. This document turns the accepted promotion/calibration rules into a single per-model readiness matrix and checklist.

A model may not be treated as production-promoted merely because its contract, selected learned scheme, deterministic pilot generator, fixture tests, registry score names, or local evaluation helpers exist.

## Active Learned Scheme Matrix

These are the accepted current learned schemes. They define the route to train and evaluate next; they do not imply production approval.

| Model | Active learned scheme | Why this shape |
|---|---|---|
| `M01 BackgroundContextModel` | `continual_gru_context_estimator` | Market/regime context is short-sequence state; CPU-friendly GRU keeps temporal memory without the cost of Transformer attention. |
| `M02 TargetStateModel` | `continual_pairwise_residual_mlp_target_ranker` | Target selection is cross-sectional ranking over dense anonymous state vectors; pairwise residual MLP fits the ranking objective without sequence overhead. |
| `M03 EventStateModel` | `continual_gru_event_risk_scorer` | Event impact depends on ordered event/state evolution; GRU captures persistence and decay in a compact recurrent state. |
| `M04 UnifiedDecisionModel` | `continual_residual_mlp_policy_value` | Final trade utility is nonlinear dense-state interaction across upstream layer outputs, costs, risk, and exposure. |
| `M05 OptionExpressionModel` | `continual_residual_mlp_option_chain_ranker` | Option expression is candidate ranking over chain attributes and M04 intent; dense residual scoring is the direct fit. |
| `M03 EventStateModel` | `continual_gru_event_risk_scorer` | Residual risk is sequence-sensitive governance; GRU keeps event/risk memory while deterministic guardrails remain hard constraints. |

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
| `M01 BackgroundContextModel` | `background_context_state` | deferred: active learned scheme selected; deterministic pilot and current-chain historical replay support exist | GRU layer-specific broad-sample labels, stability, leakage, calibration, and walk-forward evidence missing |
| `M02 TargetStateModel` | `target_context_state` | deferred: active learned scheme selected; deterministic pilot and current-chain historical replay support exist | pairwise-ranker target-state labels, leakage checks, calibration, stability, and walk-forward evidence missing |
| `M03 EventStateModel` | `event_state_vector` | deferred: active learned scheme selected; deterministic pilot and current-chain historical replay support exist | GRU event-family labels, event persistence/decay validation, leakage checks, calibration, and stability evidence missing |
| `M04 UnifiedDecisionModel` | `thesis_distribution_surface`, derived `unified_decision_vector` | deferred: active learned scheme selected; deterministic pilot and non-degenerate current-chain replay behavior exist | residual-MLP utility labels, broader walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and promotion metrics missing |
| `M05 OptionExpressionModel` | `expression_probability_surface`, derived `option_expression_plan` / `expression_vector` | deferred: active learned scheme selected; deterministic option-expression replay behavior exists | residual-MLP option-expression labels, cost/fill/theta/IV validation, leakage checks, ranking calibration, and stability evidence missing |
| `M03 EventStateModel` | `component_event_risk_control` / packet eligibility | deferred: active learned scheme selected; deterministic guardrails and standardized-event replay behavior exist | GRU residual-event labels, overblock/accounting metrics, calibration, leakage checks, stability, and hard-guardrail interaction evidence missing |

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

Promotion readiness evidence targets the six current model contracts directly.

## Implementation Hook

`src/model_governance/promotion/readiness.py` owns the lightweight reusable validation helper for this checklist. It verifies required evidence fields and gate results; it does not approve models by itself.

`scripts/models/run_current_model_historical_evaluation.py` is the historical replay/training evidence runner for the current five-model chain. It can produce `current_model_historical_evaluation_receipt`, governance table-shaped evidence rows, input-coverage diagnostics, non-degenerate M04/M05 distribution evidence, and a local cumulative residual-MLP utility baseline artifact from bounded point-in-time historical rows. This runner is evidence production only; passing it does not satisfy the full per-model promotion package or authorize activation.

Latest existing-data replay evidence: `current_chain_retrain_replay_20260622T0903_et` produced 750 current-chain rows over 2021Q1, trained the local cumulative residual-MLP utility baseline artifact, joined mature labels for every row, covered 19 unique routing symbols, and returned `evaluation_status = passed` with `warning_reasons = []`. Activation and production promotion remained disallowed. The artifact is stored at `/root/projects/trading-storage/storage/03_model_artifacts/current_chain_retrain_replay_20260622T0903_et/current_model_historical_evaluation.json`.

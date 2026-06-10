# Promotion Acceptance

Status: accepted current production-promotion evidence receipt; no production activation
Date: 2026-06-10

## Summary

No current six-model contract is production-promoted by this acceptance evidence.

`trading-model` owns evidence generation and reviewer artifacts only:

- model outputs;
- labels;
- evaluation runs;
- promotion metrics;
- candidate evidence packages;
- reviewer artifacts.

Durable promotion requests, review decisions, activation, rollback, and production pointers belong in `trading-manager` through the unified `model_promotion_review` path.

## Current Readiness Receipt

| Model | Evidence state | Current status | Activation |
|---|---|---|---|
| `model_01_background_context` | current six-model implementation/evaluation missing | deferred | none |
| `model_02_target_state` | current six-model implementation/evaluation missing | deferred | none |
| `model_03_event_state` | current six-model implementation/evaluation missing | deferred | none |
| `model_04_unified_decision` | first unified decision pilot missing | deferred | none |
| `model_05_option_expression` | current six-model implementation/evaluation missing | deferred | none |
| `model_06_residual_event_governance` | current six-model implementation/evaluation missing | deferred | none |

## Migration Evidence

Retired ten-layer evaluation artifacts remain useful negative and migration evidence. They are not production approval for the current six-model route.

The model repo may reuse retired implementation packages and evidence while migrating, but durable review requests and decisions must be submitted through `trading-manager` against the current six model contracts.

## Blockers

- M01 requires merged background-context generation/evaluation evidence.
- M02 requires target-state generation/evaluation evidence under the current M01 context.
- M03 requires event-state generation/evaluation evidence from accepted event-family inputs.
- M04 requires unified decision training/evaluation with structured edge/risk/exposure/action heads.
- M05 requires option-chain replay and option-expression / base trading-guidance outcome evidence.
- M06 requires real residual-event-governance labels and production evaluation metrics.

## Activation Invariant

No production config is active from this acceptance pass. Deferred reviews must not create runtime activation records or move active config pointers. Runtime activation records and active-pointer writes belong in `trading-execution`.

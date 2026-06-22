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

The local current-chain runner emits `current_model_chain_receipt` for fixture smoke evidence only. A passed receipt proves current-contract handoffs, label-leakage checks, and retired-field absence for the deterministic pilot path; it does not approve production promotion.

## Current Readiness Receipt

| Model | Evidence state | Current status | Activation |
|---|---|---|---|
| `model_01_background_context` | deterministic background-context implementation present; current-chain historical replay can consume point-in-time context | deferred | historical evidence only |
| `model_02_target_state` | deterministic target-state implementation present; target-return direction normalization supports replay behavior | deferred | historical evidence only |
| `model_03_event_state` | deterministic event-state implementation present; current-chain historical replay can pass accepted event context downstream | deferred | historical evidence only |
| `model_04_unified_decision` | deterministic unified decision pilot present; current-chain historical replay now produces non-degenerate action distributions | deferred | historical evidence only |
| `model_05_option_expression` | deterministic M04-intent option-expression implementation present; current-chain historical replay now produces point-in-time `long_call` / `long_put` expression rows when candidates pass filters | deferred | historical evidence only |
| `model_06_residual_event_governance` | deterministic M04/M05-thesis residual-governance implementation present; current-chain historical replay now consumes standardized `event_interpretation_v1` and produces non-degenerate intervention rows | deferred | historical evidence only |

The current-chain receipt gate is available through:

```text
scripts/models/run_current_model_chain.py --receipt-only
```

The current-chain historical replay/training gate is available through:

```text
scripts/models/run_current_model_historical_evaluation.py
```

Latest existing-data replay evidence is `current_chain_retrain_replay_20260622T0903_et`, stored at `/root/projects/trading-storage/storage/03_model_artifacts/current_chain_retrain_replay_20260622T0903_et/current_model_historical_evaluation.json`. It passed with a trained local utility baseline, 750 generated chain rows, 100% mature label coverage, non-degenerate M04/M05/M06 distributions, and no warning reasons. This is historical evidence only, not promotion approval or runtime activation.

## Migration Evidence

Retired serial evaluation artifacts remain useful negative and migration evidence. They are not production approval for the current six-model route.

Durable review requests and decisions must be submitted through `trading-manager` against the current six model contracts.

## Blockers

- M01 has a deterministic background-context generator. It still requires real broad-market/sector datasets, background labels, walk-forward baselines, leakage checks, and calibration evidence.
- M02 has a deterministic target-state generator that consumes M01 context and sanitizes model-facing identity fields. It still requires real target-state datasets, anonymous target labels, baselines, leakage checks, and calibration evidence.
- M03 has a deterministic event-state generator that consumes accepted event contracts as frozen inputs. It still requires real accepted-event datasets, event response/risk labels, baselines, leakage checks, and calibration evidence.
- M04 has a deterministic structured-head generator and non-degenerate historical current-chain replay behavior. It still requires direct utility labels, broader walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and real promotion evidence.
- M05 has a deterministic implementation that consumes M04 `direct_underlying_intent` and can select point-in-time option expressions during historical replay. It still requires option-expression outcome labels, cost/fill/theta/IV validation, baseline comparison, leakage checks, and calibration evidence.
- M06 has a deterministic implementation that consumes M04 `unified_decision_vector_ref`, optional M05 `option_expression_plan_ref`, and standardized event interpretations during historical replay. It still requires residual-event-governance labels, overblock/accounting metrics, calibration, stability, and production evaluation evidence.

## Activation Invariant

No production config is active from this acceptance pass. Deferred reviews must not create runtime activation records or move active config pointers. Runtime activation records and active-pointer writes belong in `trading-execution`.

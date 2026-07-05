# Promotion Acceptance

Status: accepted current production-promotion evidence receipt; no production activation
Date: 2026-06-10

## Summary

No current five-model contract is production-promoted by this acceptance evidence. The active learned scheme route is selected separately from production promotion.

`trading-model` owns evidence generation and reviewer artifacts only:

- model outputs;
- labels;
- evaluation runs;
- promotion metrics;
- candidate evidence packages;
- reviewer artifacts.

Durable promotion requests, review decisions, activation, rollback, and production pointers belong in `trading-manager` through the unified `model_promotion_review` path.

Current accepted learned schemes:

- `M01`: `continual_gru_context_estimator`
- `M02`: `continual_pairwise_residual_mlp_target_ranker`
- `M03`: `continual_gru_event_risk_scorer`
- `M04`: `continual_residual_mlp_policy_value`
- `M05`: `continual_residual_mlp_option_chain_ranker`

The local current-chain runner emits `current_model_chain_receipt` for fixture smoke evidence only. A passed receipt proves current-contract handoffs, label-leakage checks, and retired-field absence for the deterministic pilot path; it does not approve production promotion.

## Current Readiness Receipt

| Model | Evidence state | Current status | Activation |
|---|---|---|---|
| `model_01_background_context` | GRU context scheme selected; deterministic background-context implementation present; current-chain historical replay can consume point-in-time context | deferred | historical evidence only |
| `model_02_target_state` | pairwise residual-MLP ranker selected; deterministic target-state implementation present; target-return direction normalization supports replay behavior | deferred | historical evidence only |
| `model_03_event_state` | GRU event-risk scheme selected; deterministic event-state implementation present; current-chain historical replay can pass accepted event context downstream | deferred | historical evidence only |
| `model_04_unified_decision` | residual-MLP policy-value scheme selected; deterministic unified decision pilot present; current-chain historical replay produces non-degenerate action distributions | deferred | historical evidence only |
| `model_05_option_expression` | residual-MLP option-chain ranker selected; deterministic M04-intent option-expression implementation present; current-chain historical replay produces point-in-time `long_call` / `long_put` expression rows when candidates pass filters | deferred | historical evidence only |

The current-chain receipt gate is available through:

```text
scripts/models/run_current_model_chain.py --receipt-only
```

The current-chain historical replay/training gate is available through:

```text
scripts/models/run_current_model_historical_evaluation.py
```

Latest existing-data replay evidence is `current_chain_retrain_replay_20260622T0903_et`, stored at `/root/projects/trading-storage/storage/03_model_artifacts/current_chain_retrain_replay_20260622T0903_et/current_model_historical_evaluation.json`. It passed with a trained local cumulative residual-MLP utility baseline artifact, 750 generated chain rows, 100% mature label coverage, non-degenerate M04/M05 distributions, and no warning reasons. This is historical evidence only, not promotion approval or runtime activation.

## Migration Evidence

Retired serial evaluation artifacts remain useful negative and migration evidence. They are not production approval for the current five-model route.

Durable review requests and decisions must be submitted through `trading-manager` against the current five model contracts.

## Blockers

- M01 has selected `continual_gru_context_estimator` and a deterministic background-context generator. It still requires real broad-market/sector sequence datasets, background labels, walk-forward evidence, leakage checks, and calibration evidence.
- M02 has selected `continual_pairwise_residual_mlp_target_ranker` and a deterministic target-state generator that consumes M01 context and sanitizes model-facing identity fields. It still requires real target-state datasets, anonymous target labels, leakage checks, ranking calibration, and stability evidence.
- M03 has selected `continual_gru_event_risk_scorer` and a deterministic event-state generator that consumes accepted event contracts as frozen inputs. It still requires real accepted-event datasets, event response/risk labels, persistence/decay checks, leakage checks, and calibration evidence.
- M04 has selected `continual_residual_mlp_policy_value`, a deterministic structured-head generator, and non-degenerate historical current-chain replay behavior. It still requires direct utility labels, broader walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and real promotion evidence.
- M05 has selected `continual_residual_mlp_option_chain_ranker` and a deterministic implementation that consumes M04 `direct_underlying_intent` and can select point-in-time option expressions during historical replay. It still requires option-expression outcome labels, cost/fill/theta/IV validation, leakage checks, ranking calibration, and stability evidence.

## Activation Invariant

No production config is active from this acceptance pass. Deferred reviews must not create runtime activation records or move active config pointers. Runtime activation records and active-pointer writes belong in `trading-execution`.

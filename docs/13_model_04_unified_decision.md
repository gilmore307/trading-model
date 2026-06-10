# Model 04 Unified Decision

Status: accepted current model contract; deterministic implementation pilot present; promotion evidence deferred.

## Role

`M04 Unified Decision` owns the direct-underlying decision that previously passed through separate alpha, dynamic risk, position projection, and underlying action contracts. It is the main merge intended to reduce serial error propagation.

## Output

```text
model_04_unified_decision
  -> unified_decision_vector
```

The vector must expose structured heads for:

- edge / after-cost alpha;
- risk policy and risk constraints;
- exposure / size / position projection;
- direct-underlying action thesis, including no-trade and invalidation profile.

Those heads are fields of one current model contract, not separate current model contracts.

The current pilot lives in `src/models/model_04_unified_decision/` and emits `4_*` fields plus `unified_decision_vector_ref`. It keeps the edge, risk, exposure, and action heads inside one output and does not expose retired `alpha_confidence_vector`, `dynamic_risk_policy_state`, `position_projection_vector`, or `underlying_action_plan` outputs. Local generate/evaluate/review entrypoints live under `scripts/models/model_04_unified_decision/`.

## Inputs

- `background_context_state`.
- `target_context_state`.
- `event_state_vector`.
- Replay-safe portfolio/risk context, quote/liquidity/borrow, cost/friction, and current/pending exposure state.

## Migration Source

Retired packages `model_05_alpha_confidence`, `model_06_dynamic_risk_policy`, `model_07_position_projection`, and `model_08_underlying_action` may be used as source material during migration. They are not separate current model contracts.

## Current Gate

The pilot is a deterministic contract implementation and local fixture generator. Production promotion still requires point-in-time training data, direct utility labels, walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and manager-side promotion review.

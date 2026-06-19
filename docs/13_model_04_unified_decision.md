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

`4_target_allocation_fraction_<horizon>` and `4_resolved_target_allocation_fraction` are model-owned target allocation percentages of total portfolio/account budget. Execution and replay components may convert the resolved fraction into notional dollars and option contract quantity, but must not invent the allocation percentage themselves.

M04 does not emit executable tactical add actions. When an existing same-direction position has positive incremental gap, the current executable action is `maintain`; full-account operation lets winners grow by mark-to-market weight rather than tactical add orders. Risk-reduction actions such as `reduce_long`, `reduce_short`, `close_long`, and `cover_short` remain valid.

`4_trade_intensity_score_<horizon>` remains the raw material exposure-gap magnitude. Horizon resolution uses `4_materiality_adjusted_action_score_<horizon>` so raw intensity first has to clear the configured materiality gate, then confidence, entry quality, downside risk, and no-trade pressure rank the action.

## Inputs

- `background_context_state`.
- `target_context_state`.
- `event_state_vector`.
- Replay-safe portfolio/risk context, quote/liquidity/borrow, cost/friction, and current/pending exposure state.

## Current Gate

The pilot is a deterministic contract implementation and local fixture generator. Production promotion still requires point-in-time training data, direct utility labels, walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and manager-side promotion review.

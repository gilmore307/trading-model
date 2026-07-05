# Model 04 Unified Decision

Status: accepted current model contract; deterministic implementation pilot present; promotion evidence deferred.

## Role

`M04 Unified Decision` owns the direct-underlying decision that previously passed through separate alpha, dynamic risk, position projection, and underlying action contracts. It is the main merge intended to reduce serial error propagation.

## Output

```text
model_04_unified_decision
  -> unified_decision_vector
  -> thesis_distribution_surface
```

The vector must expose structured heads for:

- edge / after-cost alpha;
- risk policy and risk constraints;
- exposure / size / position projection;
- point-in-time direction thesis and certainty;
- direct-underlying action eligibility, including no-trade and invalidation profile.

Those heads are fields of one current model contract, not separate current model contracts.

`thesis_distribution_surface` is the current PIT forecast contract for the
underlying thesis. It is not a static two-dimensional PDF. It is a conditional
return distribution surface:

```text
P(underlying return bucket at horizon tau | PIT context, target, asof)
```

The current axis contract is:

- `x`: underlying return bucket;
- `t`: forecast horizon;
- `y`: conditional probability.

The current production-compatible implementation still emits the existing M04
horizons `10min`, `1h`, `1D`, and `1W`; it exposes horizon-level return
quantiles, CDF thresholds, upside/downside probability, tail-loss probability,
uncertainty spread, and skew proxy. Future realized returns are evaluation
labels only and must not enter the emitted surface.

The accepted research migration target is
`tradable_time_return_distribution_surface`: a single calendar-aware conditional
surface over an equal-step tradable-time target grid. For US equity pilots the
current grid uses 10-minute anchors and 10-minute future target steps through
the configured future window. Closed-session time does not advance
`tau_trading_minutes`; the row still records `tau_calendar_minutes`,
session-gap counts, and open/close context. Open, close, overnight, 2D, and 3D
effects are target-row context features and validation slices, not separate
label heads or independent models.

Reusable pilot code lives in `src/models/return_distribution_surface/`; the
read-only SQL entrypoint is
`scripts/models/run_tradable_time_distribution_surface_pilot.py`.

The current pilot lives in `src/models/model_04_unified_decision/` and emits `4_*` fields plus `unified_decision_vector_ref`. It keeps the edge, risk, exposure, and action heads inside one output and does not expose retired `alpha_confidence_vector`, `dynamic_risk_policy_state`, `position_projection_vector`, or `underlying_action_plan` outputs. Local generate/evaluate/review entrypoints live under `scripts/models/model_04_unified_decision/`.

`4_target_allocation_fraction_<horizon>` and `4_resolved_target_allocation_fraction` are model-owned target allocation percentages of total portfolio/account budget. For the current fixed-slot equity/options policy, an orderable entry carries the intended slot fraction, normally `0.20`; risk, confidence, no-trade pressure, and event pressure affect eligibility, ranking, and rejection rather than silently shrinking an accepted orderable slot into a fractional position. Execution and replay components convert the resolved fraction into notional dollars and option contract quantity by using the target notional as a floor and rounding listed-option contracts up to whole contracts, subject to affordability and explicit overfill/rejection rules.

M04 does not emit executable tactical add actions. When an existing same-direction position has positive incremental gap, the current executable action is `maintain`; full-account operation lets winners grow by mark-to-market weight rather than tactical add orders. Risk-reduction actions such as `reduce_long`, `reduce_short`, `close_long`, and `cover_short` remain valid.

`4_trade_intensity_score_<horizon>` remains the raw material exposure-gap magnitude. Horizon resolution uses `4_materiality_adjusted_action_score_<horizon>` so raw intensity first has to clear the configured materiality gate, then confidence, entry quality, downside risk, and no-trade pressure rank the action.

Direction and trade eligibility are separate contract facts. `4_direction_thesis_score_<horizon>` /
`4_resolved_direction_thesis` carry the signed bullish, bearish, or neutral path view;
`4_direction_certainty_score_<horizon>` / `4_resolved_direction_certainty_score`
carry confidence without sign; `4_resolved_trade_eligibility_status` records whether
the direct-underlying action is eligible or blocked by no-trade, materiality, or direct
short policy. A blocked direct short must not erase a bearish thesis before M05 option
expression.

M04 owns the source thesis and distribution surface. M05 may consume the surface
to compare expression candidates, but M05 must not relitigate M04's target-level
direction thesis.

## Inputs

- `background_context_state`.
- `target_context_state`.
- `event_state_vector`.
- Replay-safe portfolio/risk context, quote/liquidity/borrow, cost/friction, and current/pending exposure state.

## Current Gate

The pilot is a deterministic contract implementation and local fixture generator. Production promotion still requires point-in-time training data, multi-horizon distribution labels, direct utility labels, walk-forward replay, no-trade calibration, cost/fill sensitivity, leakage checks, and manager-side promotion review.

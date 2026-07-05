# Model 03 Event State

Status: deterministic pilot present; production promotion deferred.

## Role

`M03 Event State` owns event-conditioned response, uncertainty, failure-risk mapping, distribution-effect channel state, and point-in-time event impact-channel state from accepted event-universe contracts. It consumes frozen event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, and M06-governed event impact attributes. It must not mutate those event parameters or create a competing event taxonomy.

The current event route is:

1. Materialize the full point-in-time event universe inside the fold window.
2. Run semantic interpretation and assign the event to the reviewed multi-level
   taxonomy: source category, domain node, mechanism family, optional child
   family, and optional dossier.
3. For each event family, test whether its PIT parameters can identify a
   probability function for later market/sector/target impact.
4. If a stable probability function is identifiable, M03 may expose the
   reviewed distribution channels that the family is allowed to affect.
5. If no stable probability function is identifiable, M03 may still expose
   risk-shape channels such as variance, tail, confidence, and gate pressure,
   but it must not move the center of the distribution.

## Output

```text
model_03_event_state
  -> event_state_vector
```

The output may include event response strength, permissioned direction tendency,
uncertainty, path risk, entry/cap/disable pressure, applicability confidence,
distribution-effect scores, and impact-channel scores. It must not emit
standalone event alpha or choose exposures/actions/options.

M03 owns only the event residual factor. M01 background and M02 target state may
condition event applicability, scope, and calibration slices, but M03 must not
re-count market/background contribution or target-base contribution as event
alpha.

Current local implementation emits:

- `event_state_vector_ref`
- `background_context_state_ref`
- `target_context_state_ref`
- `event_state_vector`
- `3_event_response_direction_score_<horizon>`
- `3_event_response_strength_score_<horizon>`
- `3_event_uncertainty_score_<horizon>`
- `3_event_path_risk_score_<horizon>`
- `3_event_entry_block_pressure_score_<horizon>`
- `3_event_exposure_cap_pressure_score_<horizon>`
- `3_event_strategy_disable_pressure_score_<horizon>`
- `3_event_applicability_confidence_score_<horizon>`
- `3_event_underlying_price_impact_score_<horizon>`
- `3_event_option_price_impact_score_<horizon>`
- `3_event_volatility_surface_impact_score_<horizon>`
- `3_event_option_liquidity_spread_impact_score_<horizon>`
- `3_event_expiry_gamma_flow_impact_score_<horizon>`
- `3_event_mean_shift_score_<horizon>`
- `3_event_mode_shift_score_<horizon>`
- `3_event_directional_contribution_score_<horizon>`
- `3_event_variance_multiplier_score_<horizon>`
- `3_event_left_tail_delta_score_<horizon>`
- `3_event_right_tail_delta_score_<horizon>`
- `3_event_skew_delta_score_<horizon>`
- `3_event_confidence_discount_score_<horizon>`
- `3_event_gate_pressure_score_<horizon>`

## Distribution Effect Permissions

Each accepted event row carries or inherits an `allowed_effect_profile`. The
profile is a permission mask, not the learned effect. M03 training estimates and
validates magnitudes only inside allowed channels.

Default profile:

```text
can_change_variance=true
can_change_left_tail=true
can_change_right_tail=true
can_change_skew=true
can_change_confidence=true
can_raise_gate=true
can_change_mean=false
can_change_mode=false
can_add_directional_contribution=false
```

This means ordinary events default to distribution-shape and risk-control
effects. They may widen variance, thicken tails, discount confidence, or raise
entry/gate pressure. They do not move the mean, mode, or directional
contribution unless the event family has passed a separate directional
modelability review.

Directional channels are opt-in:

```text
can_change_mean=true
can_change_mode=true
can_add_directional_contribution=true
```

These permissions are reserved for reviewed event families or dossiers with
stable PIT-identifiable direction after M01/M02 controls. Examples include hard
negative corporate/regulatory events when the family evidence supports a signed
effect. A raw `direction_bias_score` on an event row is not enough to move the
distribution center; the profile must grant the directional channel first.

M03 publishes the active per-event permissions in
`event_state_vector.allowed_effect_profiles` and the horizon summaries in
`event_state_vector.distribution_effect_scores`.

## Impact Channels

Some event families affect option prices more than the underlying price. Scheduled option-expiration events, triple witching, expiry/gamma flow, volatility-surface dislocation, and option liquidity/spread disruption are event attributes, not component logic and not local M05 taxonomy.

M03 is the runtime surface that applies these M06-governed attributes point-in-time. It must represent them as simultaneous channels rather than a binary underlying-vs-option label:

- `underlying_price`
- `option_price`
- `volatility_surface`
- `option_liquidity_spread`
- `expiry_gamma_flow`

`M04 Unified Decision` consumes the full event state for decision consequence. `M05 Option Expression` consumes the option-related channels for expression consequence, but does not redefine event identity or event-family semantics.

## Inputs

- `background_context_state`.
- `target_context_state`.
- Accepted event-family contracts from `M06 Residual Event Governance`.
- Matched-control and impact-window evidence frozen before current-fold inference.

## Review Path

Post-replay review must score M03 independently on the point-in-time event pool,
one event row at a time. The review joins each event-state row to event-window
outcome, overblock, underblock, path-deviation, and applicability labels. It
must use the pre-replay event ledger and must not create new same-fold event
inputs from selected replay trades or failures.

Missing event outcome labels are a review evidence gap, not evidence that M04 is
responsible. If M03 rows are independently acceptable while final selected
performance is poor, attribution moves downstream to M04 unless an explicit
M03-to-M04 handoff defect is shown.

## Current Local Scripts

```text
scripts/models/model_03_event_state/generate_model_03_event_state.py
scripts/models/model_03_event_state/evaluate_model_03_event_state.py
scripts/models/model_03_event_state/review_event_state_promotion.py
```

These scripts produce fixture/local evidence only and must defer production activation.

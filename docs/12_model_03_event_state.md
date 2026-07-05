# Model 03 Event State

Status: deterministic pilot present; production promotion deferred.

## Role

`M03 Event State` owns event-conditioned response, uncertainty, failure-risk mapping, distribution-effect channel state, and point-in-time event impact-channel state from accepted event-universe contracts. It consumes frozen event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, and reviewed event-impact attributes. It must not mutate those event parameters or create a competing event taxonomy.

The current event route is:

1. Materialize the full point-in-time event universe inside the fold window.
2. Run semantic interpretation and assign the event to the finest reviewed
   point-in-time taxonomy node on the fixed
   `Domain -> Kingdom -> Phylum -> Class -> Order -> Family -> Genus -> Species`
   spine. This is the `semantic_node`.
3. Select the deepest evidence-supported `effect_model_node` for training or
   fallback. It may be the semantic node or a conservative ancestor.
4. For the effect-model node, test whether its PIT parameters can identify a
   probability function for later market/sector/target impact.
5. If a stable probability function is identifiable, M03 may expose the
   reviewed distribution channels owned by that node's `event_effect_model`.
6. If no stable probability function is identifiable, M03 may still expose
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

## Event Effect Models

Each accepted event row carries or inherits an `event_effect_model` from the
evidence-supported taxonomy node. This is an impact-mode contract, not a
permission mask.

The default effect model is risk-shape only:

```text
event_effect_model_type=variance_tail_event
projection_mode=context_only_projection
distribution_channels=
  variance_multiplier
  left_tail_delta
  right_tail_delta
  skew_delta
  confidence_discount
  gate_pressure
directional_mean_shift_status=not_identifiable
```

This means ordinary events default to distribution-shape and risk-control
effects. They may widen variance, thicken tails, discount confidence, or raise
entry/gate pressure. They do not move the mean, mode, or directional
contribution unless the effect-model node has passed directional modelability
review and lists the center channels in its distribution channel contract.

Directional effect models may include:

```text
mean_shift
mode_shift
directional_contribution
```

These channels are reserved for taxonomy nodes with stable PIT-identifiable
signed residual effects after M01/M02 controls. A raw `direction_bias_score` on
an event row is not enough to move the distribution center; the node's
`event_effect_model` must be directional and fold-frozen before M03 can emit
center-moving summaries.

M03 publishes the active per-event models in
`event_state_vector.event_effect_models` and the horizon summaries in
`event_state_vector.distribution_effect_scores`.

## Impact Channels

Some event families affect option prices more than the underlying price. Scheduled option-expiration events, triple witching, expiry/gamma flow, volatility-surface dislocation, and option liquidity/spread disruption are event attributes, not component logic and not local M05 taxonomy.

M03 is the runtime surface that applies these reviewed event attributes point-in-time. It must represent them as simultaneous channels rather than a binary underlying-vs-option label:

- `underlying_price`
- `option_price`
- `volatility_surface`
- `option_liquidity_spread`
- `expiry_gamma_flow`

`M04 Unified Decision` consumes the full event state for decision consequence. `M05 Option Expression` consumes the option-related channels for expression consequence, but does not redefine event identity or event-family semantics.

## Inputs

- `background_context_state`.
- `target_context_state`.
- Accepted event-family contracts and M03 event-effect-model evidence.
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

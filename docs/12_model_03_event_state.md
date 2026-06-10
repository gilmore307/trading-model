# Model 03 Event State

Status: deterministic pilot present; production promotion deferred.

## Role

`M03 Event State` owns event-conditioned response, uncertainty, and failure-risk mapping from accepted residual-event governance contracts. It consumes frozen event-family identity, point-in-time clocks, scope, visibility, selected impact windows, and allowed use. It must not mutate those event parameters.

## Output

```text
model_03_event_state
  -> event_state_vector
```

The output may include event response strength, direction tendency, uncertainty, path risk, entry/cap/disable pressure, and applicability confidence. It must not emit standalone event alpha or choose exposures/actions/options.

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

## Inputs

- `background_context_state`.
- `target_context_state`.
- Accepted event-family contracts from `M06 Residual Event Governance`.
- Matched-control and impact-window evidence frozen before current-fold inference.

## Migration Source

Retired implementation package `model_04_event_failure_risk` and event-family helpers under retired `model_10_event_risk_governor` may be used as source material during migration. They are not separate current model contracts.

## Current Local Scripts

```text
scripts/models/model_03_event_state/generate_model_03_event_state.py
scripts/models/model_03_event_state/evaluate_model_03_event_state.py
scripts/models/model_03_event_state/review_event_state_promotion.py
```

These scripts produce fixture/local evidence only and must defer production activation.

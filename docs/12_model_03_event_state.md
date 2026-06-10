# Model 03 Event State

Status: accepted current model contract; implementation migration required.

## Role

`M03 Event State` owns event-conditioned response, uncertainty, and failure-risk mapping from accepted residual-event governance contracts. It consumes frozen event-family identity, point-in-time clocks, scope, visibility, selected impact windows, and allowed use. It must not mutate those event parameters.

## Output

```text
model_03_event_state
  -> event_state_vector
```

The output may include event response strength, direction tendency, uncertainty, path risk, entry/cap/disable pressure, and applicability confidence. It must not emit standalone event alpha or choose exposures/actions/options.

## Inputs

- `background_context_state`.
- `target_context_state`.
- Accepted event-family contracts from `M06 Residual Event Governance`.
- Matched-control and impact-window evidence frozen before current-fold inference.

## Migration Source

Retired implementation package `model_04_event_failure_risk` and event-family helpers under retired `model_10_event_risk_governor` may be used as source material during migration. They are not separate current model contracts.

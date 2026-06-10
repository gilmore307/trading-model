# model_03_event_state

Canonical package boundary for current `M03 Event State`.

This model consumes accepted residual-event governance focus-pool contracts as frozen qualitative and time-parameter inputs. It owns quantitative event response, uncertainty, failure-risk, path-risk, entry/cap/disable pressure, and applicability confidence. It must not mutate event-family parameters or emit standalone event alpha.

The current deterministic pilot consumes `background_context_state`, `target_context_state`, and accepted event contracts, then emits `event_state_vector`, `event_state_vector_ref`, and `3_event_*` scores. It records frozen event refs and blocks event-family parameter mutation.

Retired `model_04_event_failure_risk` and event-family helpers under `model_10_event_risk_governor` remain migration-source surfaces only.

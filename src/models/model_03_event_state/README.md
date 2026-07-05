# model_03_event_state

Canonical package boundary for current `M03 Event State`.

This model consumes accepted event-universe contracts as frozen qualitative and time-parameter inputs. It owns quantitative event response, uncertainty, failure-risk, path-risk, distribution-effect channels, entry/cap/disable pressure, and applicability confidence. It must not mutate event-family parameters or emit standalone event alpha.

The current deterministic pilot consumes `background_context_state`, `target_context_state`, and accepted event contracts, then emits `event_state_vector`, `event_state_vector_ref`, and `3_event_*` scores. It records frozen event refs, per-event `allowed_effect_profile` masks, impact-channel scores, and distribution-effect scores.

Default event-family permissions allow variance, tail, skew, confidence, and gate effects. Mean, mode, and directional contribution remain zero unless the accepted event-family profile explicitly grants those channels after modelability review.

Historical event-failure-risk package names are not maintained current surfaces.

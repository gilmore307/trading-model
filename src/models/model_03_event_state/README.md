# model_03_event_state

Canonical package boundary for current `M03 Event State`.

This model consumes accepted event-universe contracts as frozen qualitative and time-parameter inputs. It owns quantitative event response, uncertainty, failure-risk, path-risk, distribution-effect channels, entry/cap/disable pressure, and applicability confidence. It must not mutate event-family parameters or emit standalone event alpha.

The current deterministic pilot consumes `background_context_state`, `target_context_state`, and accepted event contracts, then emits `event_state_vector`, `event_state_vector_ref`, and `3_event_*` scores. It records frozen event refs, per-event `event_effect_model` contracts, impact-channel scores, and distribution-effect scores.

The default event effect model is risk-shape only: variance, tail, skew, confidence, and gate effects. Mean, mode, and directional contribution remain zero unless the accepted effect-model node explicitly owns those channels after modelability review.

Reviewed no-impact groups use `event_impact_disposition=no_impact` and the neutral `no_impact_event` effect model. They remain visible in review coverage but contribute zero event weight to response, risk, impact, and distribution channels.

Historical event-failure-risk package names are not maintained current surfaces.

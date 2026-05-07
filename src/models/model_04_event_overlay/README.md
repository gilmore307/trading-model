# model_04_event_overlay

Layer 4 deterministic scaffold for `EventOverlayModel`.

Owns local, point-in-time conversion from visible event overview/detail rows into `event_context_vector` rows. The scaffold implements:

- `EventEncoder`-style event normalization and dedup discounting;
- `EventContextMatcher`-style target/scope relevance scoring;
- `EventOverlayScorer`-style horizon-aware core risk/quality and impact-scope scores;
- offline label joins and leakage assertions in `evaluation.py`.

Boundary: this package must not emit alpha, position, action, option contract, broker order, or future outcome fields in inference rows.

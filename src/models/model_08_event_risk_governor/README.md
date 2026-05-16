# model_08_event_risk_governor

Layer 8 deterministic scaffold for `EventRiskGovernor`.

Owns local, point-in-time conversion from visible event overview/detail rows into `event_context_vector` rows. The scaffold implements:

- `EventEncoder`-style event normalization and dedup discounting;
- `EventContextMatcher`-style target/scope relevance scoring;
- `EventOverlayScorer`-style horizon-aware core risk/quality and impact-scope scores;
- offline label joins and leakage assertions in `evaluation.py`.

Boundary: this package must not emit alpha, position, action, option contract, broker order, or future outcome fields in inference rows.

Closeout helper:

- `event_model_closeout.py` emits `event_model_closeout_report_v1`, the accepted closeout artifact for the 2026-05 event-layer redo. It records that Layer 8 closes as a bounded EventRiskGovernor / EventIntelligenceOverlay, keeps earnings/guidance in scouting, rejects broad event/option-flow/signed-guidance alpha, and preserves the downstream regeneration/deletion hold rules without mutating artifacts.

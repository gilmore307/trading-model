# model_10_event_risk_governor

Layer 10 package for `EventRiskGovernor`.

Owns local, point-in-time conversion from visible event overview/detail rows into `event_context_vector` rows. The baseline generator implements:

- `EventEncoder`-style event normalization and dedup discounting;
- `EventContextMatcher`-style target/scope relevance scoring;
- `EventOverlayScorer`-style horizon-aware core risk/quality and impact-scope scores;
- offline label joins and leakage assertions in `evaluation.py`.

Boundary: this package must not emit alpha, position, action, option contract, broker order, or future outcome fields in inference rows.

Acceptance and discovery helpers:

- `event_model_acceptance.py` emits `event_model_acceptance_report`, the accepted acceptance artifact for the 2026-05 event-layer redo. It records that Layer 10 closes as a bounded EventRiskGovernor / EventIntelligenceOverlay, keeps earnings/guidance in scouting, rejects broad event/option-flow/signed-guidance alpha, and preserves the downstream regeneration/deletion hold rules without mutating artifacts.
- `event_family_impact_window_backtest.py` owns the reusable event-vs-control impact-window scoring contract for sample and reviewed real-input event/bar CSVs.
- `event_family_impact_window_real_inputs.py` builds the 2026-06-10 seed and all-family reviewed local input routes from event-family packets, Trading Economics calendar files, SQL-retained Alpaca/GDELT rows, and point-in-time ETF bars; it emits evidence artifacts only and does not train, activate, trade, write SQL, or delete artifacts.
- `event_family_impact_window_replay.py` applies reviewed impact-window parameters to frozen replay decision rows, separating fold-calibrated event windows from production-promotion approval without changing replay, SQL, model activation, broker, or account state.
- `fold_completion.py` consolidates the fold-scoped Layer 10 family gate matrix from packet/source/control/window/replay evidence, marking fold evidence complete without upgrading incomplete families to production completion.
- `event_observation_pool_policy.py` emits `event_observation_pool_policy`, separating all-event historical research from reviewed realtime observation-pool monitoring.
- `residual_anomaly_event_discovery.py` emits `residual_anomaly_event_discovery`, starting from `base_stack_layers_01_09` evaluation residuals and searching PIT event families for explanations, observation-pool candidates, and strategy-promotion review packets.

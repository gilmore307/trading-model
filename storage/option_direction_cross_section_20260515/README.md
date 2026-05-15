# Option direction cross-section pilot — 2026-05-15

Diagnostic-only cross-section extension of the option activity direction pilot.

Scope: NVDA, JPM, XOM, LLY, RKLB on event date 2026-04-24 with 2026-05-15 near-ATM CALL/PUT contracts selected from underlying close fallback strikes.

Outputs:

- `option_direction_cross_section_events.csv` — event-level candidate direction labels.
- `option_direction_cross_section_group_stats.csv` — grouped metrics by activity hypothesis.
- `option_direction_cross_section_by_symbol.csv` — per-symbol grouped metrics.
- `report.json` — provider summary and promotion boundary.

Boundary: this is not promotion evidence. It tests whether the label shape survives outside AAPL across a small sector/cap spread.

## Headline diagnostic result

Ask-side CALL evidence was mixed but more promising than ask-side PUT evidence. Event-weighted call activity had positive 1d/10d directional underlying results but weak 5d results; put activity failed as a stable bearish signal outside a few short-horizon cases. This remains diagnostic only and must not be promoted without OI/skew/sweep/block/confidence evidence.

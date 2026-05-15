# Option Abnormality Coverage Probe — 2026-05-15

Coverage-only diagnostic for the new option abnormality evidence fields.

## Scope

- Underlying: AAPL
- Contract set: 2026-05-15 270 CALL and PUT
- Event date: 2026-04-24
- Timeframe: 5Min
- Max events: 5 per right
- Source feed: `trading-data` `11_feed_thetadata_option_event_timeline` using live ThetaData `trade_quote` rows.

## Result

All 10 emitted events were `abnormality_coverage_complete=false`. The feed now emits the required coverage fields, but the trade-quote-only task input lacks point-in-time OI/opening-vs-closing, IV-change, skew, term-structure, and underlying confirmation/divergence evidence.

This is expected and useful: the system now records real missingness instead of treating ask-side or bid-side proxy flow as final direction evidence.

## Files

- `option_abnormality_coverage_events.csv` — event-level coverage rows.
- `option_abnormality_coverage_field_summary.csv` — per-field present/missing counts.
- `report.json` — machine-readable summary and next gaps.

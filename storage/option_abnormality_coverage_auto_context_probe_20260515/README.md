# Option abnormality coverage auto-context probe — 2026-05-15

Bounded live ThetaData probe for the option event timeline auto-enrichment path. The probe is diagnostic only; it checks whether real upstream OI/IV/skew/term/underlying evidence can populate `abnormality_evidence_coverage` before any directional conclusion.

## Sample

- Underlying: AAPL
- Contract sample: 2026-05-15 270 CALL and PUT
- Event date: 2026-04-24
- Timeframe: 5Min
- Max events: 5 per right
- Auto context: enabled
- Historical Greeks interval: 1m
- OI prior date: 2026-04-23
- Term comparison expiration: 2026-05-22

## Result

- Events emitted: 10
- Coverage complete: 8
- Coverage partial: 2
- Endpoint hard blockers: 0

All ThetaData context endpoint calls succeeded. OI/OI-change, opening-vs-closing, IV-change, skew direction, term-structure direction, and underlying confirmation were populated for the events where valid point-in-time Greek rows existed.

The two partial rows are retained intentionally: they occurred at the market open before a valid non-zero IV/Greek row was available at or before the event timestamp. The feed records those values as missing rather than borrowing future rows.

## Files

- `option_abnormality_coverage_events.csv` — combined event-detail rows.
- `option_abnormality_coverage_field_summary.csv` — required-field coverage counts.
- `auto_context_request_evidence.csv` — sanitized endpoint evidence.
- `call_option_activity_event.csv` / `put_option_activity_event.csv` — event summary rows copied from the source runtime output.
- `report.json` — structured probe report.

## Interpretation

This completes the real input-chain wiring for bounded samples, but it does not promote option direction. Direction remains diagnostic until the broader cross-section and forward-label study is rerun with complete evidence gates.

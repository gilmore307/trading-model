# Option direction pilot — AAPL 2026-04-24

Diagnostic-only pilot for the option-activity directional proof gate.

Inputs were generated from ignored local `trading-data/storage/option_direction_smoke_20260515/` artifacts:

- AAPL 2026-05-15 270 CALL/PUT option event timeline rows from ThetaData `trade_quote`;
- AAPL daily underlying bars from Alpaca;
- AAPL 2026-05-15 270 CALL/PUT daily option OHLC snapshots from ThetaData.

Outputs:

- `option_direction_candidate_events.csv` — event-level candidate direction labels and forward labels.
- `option_direction_group_stats.csv` — grouped directional pilot metrics.
- `report.json` — diagnostic interpretation and promotion blockers.

Label policy: underlying directional return is sign-adjusted by bullish/bearish hypothesis; option-contract payoff for ask-side call/put events is measured as long-contract forward return and is not multiplied by bearish sign for puts.

Important boundary: this is not model-layer proof. It is a one-symbol/one-date pilot to validate the label shape and expose missing option evidence fields.

# Option direction thorough matrix — 2026-05-15

Broader diagnostic test after option abnormality auto-context enrichment.

## Scope

- Symbols: AAPL, MSFT, NVDA, AMD, JPM, XOM, CVX, LLY, PFE, COIN, TSLA, RKLB
- Event dates: 2026-04-17, 2026-04-24, 2026-05-01
- Expiration: 2026-05-15
- Term comparison expiration: 2026-05-22
- Auto context: `auto_enrich_option_context=true`, `option_context_interval=1m`
- Labels: Alpaca underlying daily bars plus ThetaData option daily OHLC closes before expiration.

## Coverage

- Total events: 841
- Complete-evidence events: 786
- Partial events: 55
- Auto-context endpoint requests: 385
- Endpoint hard blockers: 4

## Directional headline — complete evidence only

- `bullish_activity`: n=222, symbols=12, dates=3, 10d directional avg=0.051318375952140886, hit=0.5533333333333333, long-option 10d avg=0.5415367999144449.
- `bearish_activity`: n=170, symbols=12, dates=3, 10d directional avg=-0.06101755962926309, hit=0.37383177570093457, long-option 10d avg=-0.5167508194859819.

Bullish evidence remained positive overall but became less uniform than the one-date pilot. It was positive on 10d directional averages for 9/12 symbols and negative for COIN, MSFT, and PFE. Bearish evidence did not validate overall; it was negative on the aggregate 10d directional label and unstable by symbol.

Direction-neutral path expansion remains relevant: complete-evidence bullish and bearish classes both carried large 10d path ranges (~14.7% and ~14.6%), but this artifact does not include matched non-event controls, so path-expansion proof remains separate.

Ambiguous classes remain non-directional diagnostics. This is not promotion evidence.

## Hard blockers

Four auto-context endpoint calls failed, all PFE 27.5 same-strike 2026-05-22 term-structure IV requests returning ThetaData HTTP 472 for 2026-04-24 and 2026-05-01. They are recorded as hard blockers and the affected rows remain partial instead of being filled.

## Files

- `option_direction_all_events.csv`
- `option_direction_complete_evidence_events.csv`
- `option_direction_group_stats.csv`
- `option_direction_by_symbol.csv`
- `option_direction_by_symbol_date.csv`
- `auto_context_request_evidence.csv`
- `report.json`

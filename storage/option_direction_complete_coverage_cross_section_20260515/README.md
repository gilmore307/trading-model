# Option direction complete-coverage cross-section — 2026-05-15

Bounded live ThetaData/Alpaca diagnostic test after enabling option event auto-context enrichment.

## Scope

- Event date: 2026-04-24
- Expiration: 2026-05-15
- Term comparison expiration: 2026-05-22
- Prior OI date: 2026-04-23
- Symbols: AAPL, NVDA, JPM, XOM, LLY, RKLB
- Option event feed: `11_feed_thetadata_option_event_timeline` with `auto_enrich_option_context=true`
- Labels: Alpaca underlying daily bars plus ThetaData option daily OHLC closes

## Coverage result

- Total emitted events: 239
- Complete evidence events: 231
- Partial evidence events: 8
- Auto-context endpoint requests: 60
- Endpoint hard blockers: 0

Missing fields were sparse and point-in-time honest: {'iv_level_and_change': 8, 'skew_direction': 5, 'term_structure_direction': 5, 'underlying_confirmation_or_divergence': 8}. No missing field was filled from future rows.

## Directional diagnostic headline — complete evidence only

- `bullish_activity`: n=49, 10d directional underlying avg=0.0621, hit=0.816, long-option 10d avg=0.6433.
- `bearish_activity`: n=37, 10d directional underlying avg=-0.1080, hit=0.162, long-option 10d avg=-0.6969.
- Ambiguous classes remain non-directional: `mixed_or_conflicting_activity`, `bullish_activity_or_put_selling`, and `bearish_activity_or_call_selling` are not counted as signed direction proof.

Interpretation: bullish complete-evidence option activity was meaningfully positive in this one-date cross-section, especially over 10d/14d. Bearish complete-evidence activity did not validate; it had negative directional averages and poor hit rates beyond the 5d horizon. This is still diagnostic only because it is one event date and one expiration.

## Files

- `option_direction_all_events.csv` — all emitted option abnormality events.
- `option_direction_complete_evidence_events.csv` — strict `abnormality_coverage_complete=true` subset.
- `option_direction_group_stats.csv` — all-events and complete-evidence grouped stats.
- `option_direction_by_symbol.csv` — per-symbol complete-evidence directional summaries.
- `auto_context_request_evidence.csv` — sanitized context endpoint evidence.
- `report.json` — provider status, coverage counts, endpoint blockers, and promotion boundary.

## Boundary

This is diagnostic evidence, not model-layer promotion evidence. It tests whether the real input chain can support directional study on multiple symbols. Direction-neutral path expansion must remain separate from directional validation, and broader dates/symbols are required before promotion.

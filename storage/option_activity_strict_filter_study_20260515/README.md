# Option activity strict-filter study — 2026-05-15

Diagnostic follow-up after matched controls weakened the raw bullish option-abnormality result.

## Purpose

Test whether stricter candidate definitions recover an incremental relationship against matched controls.

## Tested strict filters

- `baseline_complete_directional` — current complete-evidence bullish/bearish classes.
- `opening_iv_up` — net opening OI increase plus positive IV change.
- `opening_confirming` — net opening OI increase plus underlying confirmation.
- `opening_iv_up_confirming` — net opening OI increase, IV up, and underlying confirmation.
- `opening_iv_up_front` — net opening OI increase, IV up, and front-month richening.
- `opening_iv_up_front_confirming` — all of the above plus underlying confirmation.
- `opening_iv_up_front_skew` — opening + IV up + front-month richening + direction-supportive/neutral skew.

## Result

The stricter filters did **not** rescue the relationship. Bullish strict filters became small and generally underperformed matched controls on 10d directional/path deltas. Bearish strict filters occasionally improved directional deltas, but path deltas stayed weak/negative and samples were too small.

Conclusion: current option abnormality definitions remain diagnostic/provenance evidence, not model-layer promotion evidence.

## Files

- `strict_filter_event_membership.csv`
- `strict_filter_window_pairs.csv`
- `strict_filter_variant_stats.csv`
- `report.json`

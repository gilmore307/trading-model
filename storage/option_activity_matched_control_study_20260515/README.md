# Option activity matched-control study — 2026-05-15

Matched-control diagnostic built from `/root/projects/trading-model/storage/option_direction_thorough_matrix_20260515/`.

## Purpose

Test whether complete-evidence option abnormality windows have stronger forward underlying movement than same-symbol matched non-event candidate windows.

## Matching policy

- Unit: unique `symbol` / `event_date` / `direction_hypothesis` abnormal window.
- Controls: same-symbol daily bars excluding the tested event dates.
- Match features: prior 1d absolute return, same-symbol price level, and calendar distance.
- Control selection does **not** use forward labels.
- Caveat: control dates were not separately queried through the option-event feed, so they are matched underlying control candidates, not proven no-option-abnormality dates.

## Headline

- Abnormal windows: 152
- Control windows: 456
- `bullish_activity`: 10d path-range delta -0.0010406905954418895, 10d directional delta -0.009774233004544948.
- `bearish_activity`: 10d path-range delta -0.0034225668133571136, 10d directional delta 0.007805446343204524.

Interpretation: the matched-control pass does **not** confirm a robust incremental relationship between these option-abnormality windows and stronger 10d forward price/path movement. The raw bullish signal from the thorough matrix weakens once matched same-symbol underlying controls are used. Bearish remains unconvincing.

This is still a conservative diagnostic because controls were not separately verified as no-option-abnormality dates. It is enough to block promotion, not enough to permanently reject all future refined abnormality definitions.

## Files

- `matched_abnormal_windows.csv`
- `matched_control_windows.csv`
- `matched_abnormal_vs_control_pairs.csv`
- `matched_control_group_stats.csv`
- `report.json`

# Option event-risk amplifier study — 2026-05-15

Diagnostic test of option abnormality as an event-risk amplifier rather than standalone alpha.

## Inputs

- Option abnormality matrix: `/root/projects/trading-model/storage/option_direction_thorough_matrix_20260515`
- Matched controls: `/root/projects/trading-model/storage/option_activity_matched_control_study_20260515`
- Alpaca news artifact: `/root/projects/trading-data/storage/option_event_risk_amplifier_news_20260515/runs/option_event_risk_amplifier_news_20260515/saved/equity_news.csv`

## Event proxy

Alpaca `equity_news` rows were expanded by symbol and classified with lightweight headline/summary keyword families. PIT event proximity means symbol news in the prior day or same day before the first option-abnormality event timestamp.

## Headline

- News rows: 948
- Expanded symbol-news rows: 2671
- Abnormal windows tested: 152
- PIT-news-proximate windows: 147
- Same-day PIT-news windows: 111

Raw Alpaca-news proximity did not confirm a strong event-risk amplifier edge because ordinary news was too ubiquitous: 147/152 abnormal windows had prior/same-day PIT news. Overall PIT-news-proximate windows had roughly flat/negative 10d deltas versus matched controls.

Family separation was more informative. `earnings_or_guidance_news` was the strongest small slice: 20 windows across 4 symbols with 10d absolute-return delta about +3.08 percentage points and 10d path-range delta about +1.47 percentage points. `general_company_news` was negative versus controls.

Interpretation: raw option abnormality + raw news proximity still should not be promoted. The promising route is a reviewed event-interpretation layer that separates material event families, lifecycle, known/surprise status, and surprise/magnitude before using option abnormality as an event-risk amplifier.

## Files

- `expanded_news_events.csv`
- `option_abnormality_event_proximity_pairs.csv`
- `event_risk_amplifier_group_stats.csv`
- `report.json`

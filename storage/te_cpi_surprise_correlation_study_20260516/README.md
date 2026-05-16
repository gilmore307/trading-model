# TE CPI surprise correlation study

Contract: `te_cpi_surprise_correlation_study_v1`

Uses Trading Economics visible calendar rows through the existing `trading-data` feed. Surprise is `actual - consensus` when consensus is present, otherwise `actual - te_forecast`.

Conclusion: TE actual-vs-expectation CPI surprise is useful as an abnormal macro-risk/event feature, especially for event-day path risk; it is not standalone directional alpha.

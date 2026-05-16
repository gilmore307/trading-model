# Abnormal CPI release correlation study

Contract: `abnormal_cpi_release_correlation_study_v1`

Abnormal definition: expanding historical z-score excluding current print, `abs(z) >= 1.5`, minimum 24 prior releases, over `cpi_mom, core_mom, cpi_yoy, core_yoy`.

Safety: no provider calls in this slice, no model activation, no broker/account mutation, no artifact deletion.

Conclusion: abnormal CPI prints have modest event-risk/volatility relevance but do not produce stable directional alpha. Include as an abnormal macro-risk/calendar control, not a direct trading signal.

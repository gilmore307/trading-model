# CPI release correlation study

Contract: `cpi_release_correlation_study_v1`

This diagnostic uses FRED read-only CPI release dates plus FRED CPI/Core CPI observations and already-local Alpaca ETF bar artifacts. It evaluates CPI release-day and forward returns against nearby non-event control days for liquid ETF/sector proxies with sufficient local bar coverage.

Safety:

- Provider calls: FRED read-only only
- Model activation: false
- Broker execution: false
- Account mutation: false
- Artifact deletion: false

Current conclusion: CPI release occurrence has at most weak event-risk/volatility relevance. Realized CPI level/change has weak, unstable correlation with forward ETF returns and is not suitable as standalone directional alpha. If included, it should be a macro event-risk/control feature, not a trading signal.

Primary files:

- `strict_summary.json`
- `strict_cpi_release_summary.csv`
- `strict_cpi_release_event_rows.csv`

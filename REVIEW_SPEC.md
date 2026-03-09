# Review / Replay Spec v1

## Time Zone
- All weekly review windows use Beijing time (Asia/Shanghai).
- Weekly review window: previous Sunday 00:00:00 to current Sunday 00:00:00.

## Data Retention / Aggregation
- Keep 1m OHLC for last 7 days.
- Keep 15m OHLC for last 30 days.
- Keep 1h OHLC for last 90 days.
- Keep 1d OHLC for older data.
- Weekly review job also performs data compaction.

## Review Windows
- Weekly window
- Rolling 4-week window
- Rolling 3-month window

## Core Analysis Modules
- performance metrics
- fee impact
- add-on/add-position effectiveness
- leverage effectiveness
- market regime / volatility bucket breakdown
- conservative parameter adjustment suggestions

## Explicit Exclusions
- No strategy elimination module
- No bucket elimination / kill-switch recommendations in review

## Account Reset Model
- Weekly reset of the virtual comparison account baseline
- Before local weekly reset, convert visible non-USDT account assets into USDT (after the user resets the OKX demo account on their side)
- Preserve full historical events, OHLC, reviews, and parameter changes

## Outputs
- structured JSON for dashboard
- human-readable summary
- Discord delivery
- website display

## Analysis Stack
- core metrics and scoring via local deterministic code
- optional future local ML layer
- LLM summary as explanation layer only

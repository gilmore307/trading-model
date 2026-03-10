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
- fee impact (standalone module for trading-frequency adjustment)
- add-on/add-position effectiveness
- leverage effectiveness
- market regime / volatility bucket breakdown
- conservative parameter adjustment suggestions

### Fee Module Policy
- Fee is reviewed as a standalone control module, not as a per-trade deep-dive by default.
- Primary outputs: periodic total fee, fee coverage, average fee per execution, fee-to-profit ratio when profit basis is available.
- Primary decision use: adjust trading / add-position frequency.
- If fee burden is high relative to realized profit, recommend lowering frequency.
- If fee burden is low, make no frequency adjustment from fee alone.
- Keep individual fee records only for debugging / audit, not as the main review surface.

## Explicit Exclusions
- No strategy elimination module
- No bucket elimination / kill-switch recommendations in review

## Account / Mode Model
- **calibrate** = weekly operational recalibration of the virtual comparison account baseline
- During calibrate, flatten positions, convert primary strategy-related non-USDT assets into USDT, then reset local buckets
- After calibrate completes successfully, the system should automatically return to **trade** mode
- **reset** = development-only destructive reset that clears historical trading/runtime data and returns to **develop** mode
- Preserve full historical events, OHLC, reviews, and parameter changes during calibrate; reset may clear runtime/history artifacts by design

## Outputs
- structured JSON for dashboard
- human-readable summary
- Discord delivery
- website display

## Analysis Stack
- core metrics and scoring via local deterministic code
- optional future local ML layer
- LLM summary as explanation layer only

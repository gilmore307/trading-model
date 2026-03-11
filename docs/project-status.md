# Project Status

_Last updated: 2026-03-12_

## Goal

Maintain a resumable, auditable view of the crypto-trading rebuild so future sessions can recover project state quickly without depending on chat history.

## Current state

The project has moved beyond a raw demo scaffold and now has several distinct layers in place:

1. **Runtime / mode system**
2. **Execution / state control**
3. **Review/report framework**
4. **Traceable runtime artifacts**

## Major milestones already completed

### Runtime and operations
- Reconciliation before each cycle was integrated so local tracked state is checked against exchange state before normal actions.
- The system reached a point where `trade` mode was running normally after calibrate completed.

### Review stack
- `src/review/performance.py` established a normalized per-account performance input layer.
- `src/review/aggregator.py` added history-based aggregation from execution artifacts.
- Artifact production now persists `summary.account_metrics`, making the data path more explicit. Fee is live, and equity/pnl carriage is now wired when upstream balance summaries are present.

### Verification history
- Earlier full validation: `107 passed`
- Current full validation: `111 passed`

## Open gaps

1. canonical `pnl_usdt`
2. canonical `equity_usdt`
3. clearer human-facing review summary layer
4. continued MD backfill for older areas as they are touched

## Next step

Continue upstream production of canonical `pnl_usdt` and `equity_usdt` into `summary.account_metrics`.

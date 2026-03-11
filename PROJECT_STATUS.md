# PROJECT_STATUS.md

_Last updated: 2026-03-12_

## Goal

Maintain a resumable, auditable view of the crypto-trading rebuild so future sessions can recover project state quickly without depending on chat history.

## Current state

The project has moved beyond a raw demo scaffold and now has several distinct layers in place:

1. **Runtime / mode system**
   - Mode model is established around:
     - `develop`
     - `trade`
     - `review`
     - `calibrate`
     - `reset`
     - `test`
   - User terminology was clarified and is now durable:
     - **calibrate** = normal post-flatten weekly bucket reset, then return to `trade`
     - **reset** = destructive development reset, then return to `develop`

2. **Execution / state control**
   - Local/exchange reconciliation was integrated into the run loop.
   - Route freeze / mismatch handling exists.
   - Execution artifacts are persisted under `logs/runtime/`.

3. **Review/report framework**
   - Review scaffold exists with cadence-aware report sections.
   - Performance snapshot exists for per-account metrics.
   - History aggregation from `execution-cycles.jsonl` is live.
   - Canonical ingestion path now exists for `fee_usdt`, with `pnl_usdt` and `equity_usdt` hooks prepared.

4. **Dashboard-adjacent product direction**
   - The surrounding OKX/dashboard effort already established a read-only operational UI direction, and the trading repo should continue exposing auditable artifacts instead of opaque state.

## Important already-completed milestones

### Runtime and operations
- Reconciliation before each cycle was integrated so local tracked state is checked against exchange state before normal actions.
- The system had already reached a point where `trade` mode was running normally after calibrate completed, with no persistent operational breakage in that path.

### Review stack
- `src/review/performance.py` established a normalized per-account performance input layer.
- `src/review/aggregator.py` added history-based aggregation from execution artifacts.
- Review moved from pure scaffold status to a state where it can derive:
  - `trade_count`
  - `exposure_time_pct`
  - `fee_usdt`
  - plus future-compatible `pnl_usdt` / `equity_usdt`
- Artifact production now persists `summary.account_metrics`, making the data path more explicit.

### Verification history
- Earlier milestone: review aggregator integration had already passed full test validation (`107 passed`).
- Current milestone: after canonical ingestion and account-metric persistence work, full test validation is now `109 passed`.

## Current traceable data path

### Produced at runtime
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

### Carried inside artifacts
- `summary`
- `compare_snapshot`
- `receipt`
- `summary.account_metrics`

### Aggregated by review layer
- `src/review/ingestion.py`
- `src/review/aggregator.py`
- `src/review/performance.py`
- `src/review/report.py`

## Open risks / assumptions

1. **Canonical PnL/equity source not finalized**
   - Fee has a live source path.
   - PnL/equity still need an agreed upstream producer and persistence rule.

2. **Report readability still trails data readiness**
   - Performance data is entering the system, but report presentation still needs a clearer human-facing summary layer.

3. **Project documentation is still catching up**
   - This file and `TRACEABILITY.md` start the rule, but older milestones should continue being backfilled into MD as we touch each area.

## Next step

Continue upstream work that produces canonical `pnl_usdt` and `equity_usdt` into `summary.account_metrics`, then improve report rendering so fee / pnl / equity become explicit review outputs rather than only row-level fields.

## Source notes used for backfill

This file was backfilled from durable session memory covering:
- review aggregator scaffold progress
- runtime reconcile integration
- test validation milestones
- user terminology and operational workflow clarifications

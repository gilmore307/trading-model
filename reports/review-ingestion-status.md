# Review Ingestion Status

_Last updated: 2026-03-12_

## Goal

Make review performance metrics traceable from runtime artifact production to final report aggregation.

## Current pipeline

### 1. Production point

Execution cycle artifacts now write:

- `summary.account_metrics`

Current populated metric sources:

- `fee_usdt` from `receipt.raw`
- `equity_usdt` / `pnl_usdt` from account balance summaries when available upstream

Files:

- `src/runners/execution_cycle.py`
- `src/review/account_metrics.py`

### 2. Canonical ingestion point

Review canonicalization reads metrics from:

1. `receipt.raw`
2. `summary.account_metrics`
3. `compare_snapshot.accounts` (forward-compatible)

Files:

- `src/review/ingestion.py`
- `src/review/aggregator.py`

### 3. Aggregation output

Current aggregated fields by account:

- `trade_count`
- `exposure_time_pct`
- `fee_usdt`
- `pnl_usdt` (supported if present upstream)
- `equity_usdt` (supported if present upstream)

### 4. Report surface

Current report surface:

- `metrics.performance.accounts`
- `metrics.performance.highlights`

Files:

- `src/review/performance.py`
- `src/review/report.py`

## What is live now

- Canonical fee ingestion is live
- Artifact-level `summary.account_metrics` is live
- Canonical `equity_usdt` / `pnl_usdt` can now be carried when upstream balance summaries are present
- A final always-on upstream producer for live balance snapshots is still pending

## Open gaps

1. Persist canonical `pnl_usdt`
2. Persist canonical `equity_usdt`
3. Decide source of truth for account equity snapshots per cycle/window
4. Surface fee / pnl / equity more explicitly in report sections, not only in performance snapshot rows

## Next step

Implement upstream production of canonical `pnl_usdt` and `equity_usdt` into `summary.account_metrics` so review reports stop depending on placeholders for those fields.

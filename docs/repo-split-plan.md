# Repo Split Plan: `trading-model` vs `quantitative-trading`

This document defines the intended split after renaming this repository to `trading-model`.

## Purpose of `trading-model`

`trading-model` should keep the historical / offline side of the system:

- historical data ingestion for research
- raw/intermediate/derived research data conventions
- market-state dataset construction
- regime discovery and labeling
- parameter utility datasets
- family comparison / offline evaluation
- backtests and replay-oriented research
- research reports and model-facing artifacts

## Purpose of `quantitative-trading`

`quantitative-trading` should own the realtime / live side of the system:

- live runtime workflows
- realtime trading daemons
- execution submission / confirm / reconcile
- live state persistence
- live route / strategy switching
- realtime alerts / notifications
- account/exchange operational execution glue

Repo URL:
- <https://github.com/gilmore307/quantitative-trading>

## Keep in `trading-model`

### Docs / research / historical data
- data layering docs
- time-series partition docs
- market-state and research docs
- family artifact / offline evaluation docs
- historical data ingestion docs

### Likely code to keep
- `src/research/`
- `src/regimes/`
- `src/features/`
- `src/pipeline/research_pipeline.py`
- `src/runners/backtest_research.py`
- `src/runners/build_*dataset*.py`
- `src/runners/build_*report*.py`
- `src/runners/evaluate_unsupervised_labels.py`
- `src/runners/research_pipeline.py`
- `src/runners/research_anomaly_check.py`
- `scripts/data/`
- `scripts/pipeline/`
- `scripts/research/`
- research/backtest-facing review exports that are historical-analysis oriented

## Move to `quantitative-trading`

### Realtime / execution / operations
- `src/execution/`
- `src/runtime/`
- `src/state/`
- `src/reconcile/`
- live-oriented parts of `src/market/`
- live-oriented routing / router-composite execution code
- account/exchange runtime glue used for live operation

### Likely runners / scripts to move
- `src/runners/trade_daemon.py`
- `src/runners/realtime_engine.py`
- `src/runners/execution_cycle.py`
- `src/runners/strategy_upgrade_event.py`
- `src/runners/calibrate_event.py`
- `src/runners/review_event.py`
- `src/runners/process_strategy_upgrade_request.py`
- `src/runners/promote_strategy.py`
- `src/runners/trade_alert_watcher.py`
- `src/runners/shock_monitor.py`
- `src/runners/discord_notifier.py`
- `src/runners/minute_engine.py`
- `scripts/runtime/`

## Needs judgment during migration

Some areas may split rather than move whole:

- `src/market/`
  - historical ingestion helpers may stay
  - websocket / live hub pieces should move
- `src/routing/`
  - purely offline comparison helpers may stay
  - live routing / switch policy should move
- `src/review/`
  - historical performance review may stay
  - live operations diagnostics may move
- `src/config/`
  - research-only config should stay
  - live exchange/account config should move

## Migration rule

Do not decide file-by-file based only on whether something looks old.
Instead classify by system responsibility:

- if it exists to support offline modeling / backtests / historical evaluation -> keep in `trading-model`
- if it exists to support live operation / account state / execution / realtime workflows -> move to `quantitative-trading`

## Near-term execution plan

1. finish the historical data ingestion boundary inside `trading-model`
2. classify modules into keep / move / split
3. update docs so `trading-model` no longer presents itself as a hybrid live+research repo
4. move realtime code to `quantitative-trading` in coherent chunks
5. only after the split stabilizes, delete truly obsolete leftovers

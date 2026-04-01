# Repo Split Classification v1

First-pass classification for splitting the current codebase into:

- `trading-model` (historical data / research / backtests)
- `quantitative-trading` (realtime trading / execution / live runtime)

This file is a working classification sheet, not a final migration log.

## Keep in `trading-model`

### Historical data / ingestion
- `scripts/data/fetch_okx_history_candles.py`
- `scripts/data/fetch_bitget_derivatives_context.py`
- `scripts/update_raw_monthly_data.py`
- `scripts/data_sparse_include.sh`
- `scripts/data_sparse_exclude.sh`
- `src/research/monthly_jsonl.py`

### Research / modeling / offline evaluation
- `src/research/`
- `src/regimes/`
- `src/features/`
- `src/pipeline/research_pipeline.py`
- `src/runners/backtest_research.py`
- `src/runners/build_crypto_market_state_dataset.py`
- `src/runners/build_ma_parameter_utility_dataset.py`
- `src/runners/build_donchian_parameter_utility_dataset.py`
- `src/runners/build_bollinger_parameter_utility_dataset.py`
- `src/runners/build_strategy_parameter_utility_dataset.py`
- `src/runners/build_family_market_state_report.py`
- `src/runners/build_unsupervised_market_state_baseline.py`
- `src/runners/build_unsupervised_timestamp_labels.py`
- `src/runners/evaluate_unsupervised_labels.py`
- `src/runners/build_market_discovery_web_payload.py`
- `src/runners/research_pipeline.py`
- `src/runners/research_anomaly_check.py`
- `src/runners/build_regime_dataset.py`
- `src/runners/compare_strategies.py`
- `src/runners/optimize_strategy_params.py`
- `src/runners/build_trading_overview_backtest.py`
- `scripts/research/`
- `scripts/pipeline/`
- historical/research-facing docs under `docs/`

### Historical review / reporting candidates to keep
- `src/review/history_loader.py`
- `src/review/aggregator.py`
- `src/review/performance.py`
- `src/review/export.py`
- `scripts/review/weekly_review.py`
- `scripts/review/monthly_review.py`
- `scripts/review/quarterly_review.py`
- `src/runners/weekly_review.py`
- `src/runners/monthly_review.py`
- `src/runners/quarterly_review.py`

## Move to `quantitative-trading`

### Live runtime / execution core
- `src/execution/`
- `src/runtime/`
- `src/state/`
- `src/reconcile/`
- `src/exchange/okx_client.py`
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
- `scripts/runtime/execution_cycle.py`
- `scripts/runtime/regime_snapshot.py`
- `scripts/runtime/shock_snapshot.py`
- `scripts/runtime/trade_alert_scan.py`

## Split / needs judgment

### Market data / views
- `src/market/`
  - likely keep: historical ingestion helpers and offline derived views
  - likely move: websocket, hub, and live streaming pieces

### Routing
- `src/routing/`
  - likely keep: offline comparison / simulation helpers if used by backtests or research
  - likely move: live route-switching / execution-facing policy pieces

### Review layer
- `src/review/`
  - historical performance review should stay in `trading-model`
  - live operations diagnostics should move to `quantitative-trading`

### Config
- `src/config/`
  - research-only settings should stay
  - live account / exchange operation settings likely move

### Multi-purpose runners
- `src/runners/regime_runner.py`
  - classify by whether it primarily supports offline labeling or live regime updates
- `src/runners/append_parameter_change_event.py`
  - historical audit trail may stay; live promotion workflow coupling may push it to split
- `src/runners/build_family_variant_dashboard_artifacts.py`
  - likely stay if dashboard remains a research / artifact browser rather than live operations panel

## Migration notes

### Immediate principle
Do not delete modules just because they look legacy.
If they support a responsibility that is still needed, either:
- keep them in `trading-model`, or
- move them to `quantitative-trading`

### First migration chunk suggestion
Safest first live-side chunk to move:
- `src/execution/`
- `src/runtime/`
- `src/state/`
- `src/reconcile/`
- `src/runners/trade_daemon.py`
- `src/runners/realtime_engine.py`
- `src/runners/execution_cycle.py`
- `scripts/runtime/`

This chunk has the clearest live/runtime identity.

# Project Map

This document is the high-level orientation map for the current **trading-model** codebase.

## Top-level directories

- `src/` — research, historical data, evaluation, and transitional modules pending split
- `tests/` — automated tests
- `scripts/` — operator / cron / research / ingestion entrypoints
- `logs/` — runtime and research artifacts
- `reports/` — exported research / review outputs
- `docs/` — all project Markdown

## Main code areas intended to remain

### Historical data / ingestion
- `scripts/data/` — historical data fetch and update entrypoints
- `src/research/monthly_jsonl.py` — monthly-partition loader
- data-layering / partition docs under `docs/`

### Research / modeling
- `src/research/` — offline dataset building, replay helpers, evaluators, reporting, parameter-search scaffolding
- `src/regimes/` — regime classifier logic
- `src/features/` — feature computation
- `src/runners/backtest_research.py`
- `src/runners/build_*dataset*.py`
- `src/runners/build_*report*.py`

### Historical review / reporting
- `src/review/` — keep only the parts that remain historical-analysis oriented after split
- `scripts/review/` and review runners should be evaluated by whether they serve offline history analysis or live operations

## Areas expected to move to `quantitative-trading`

### Realtime / execution
- `src/execution/`
- `src/runtime/`
- `src/state/`
- `src/reconcile/`
- live-oriented parts of `src/market/`
- live-oriented parts of `src/routing/`
- realtime/live-operation runners under `src/runners/`
- `scripts/runtime/`

## Current migration reality

### Already true
- this repo is being re-scoped toward historical modeling and backtests
- the data ingestion layer is being isolated from downstream consumers
- the repo split direction is explicit

### Transitional
- some live/runtime docs still exist here
- some live/runtime modules still remain in-tree pending migration
- some review/routing/market code still needs keep-vs-move classification

## Recommended reading order for work on this repo

1. `docs/README.md`
2. `docs/project-status.md`
3. `docs/repo-split-plan.md`
4. `docs/TODO.md`
5. `docs/data-ingestion-architecture.md`
6. relevant code modules

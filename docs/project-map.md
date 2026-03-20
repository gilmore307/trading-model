# Project Map

This document is the high-level orientation map for the current crypto-trading codebase.

## Top-level directories

- `src/` — runtime, execution, exchange, research, review, state, routing, strategy code
- `tests/` — automated tests
- `scripts/` — operator / cron entrypoints
- `logs/` — runtime and research artifacts
- `reports/` — exported review outputs
- `docs/` — all project Markdown

## Main code areas

### Runtime / execution
- `src/runners/trade_daemon.py` — live daemon entrypoint
- `src/runners/execution_cycle.py` — execution artifact builders/persistence
- `src/execution/pipeline.py` — execution cycle logic; now contains both single-cycle compatibility flow and the newer parallel-cycle path
- `src/execution/controller.py` — local state transitions, verification, reconcile, recovery markers
- `src/execution/adapters.py` — dry-run vs OKX execution backends
- `src/reconcile/` — local-vs-exchange alignment logic
- `src/state/` — persisted live position / route state

### Strategies / routing
- `src/strategies/executors.py` — strategy executors and parallel plan generation
- `src/routing/` — routing and composite/simulation helpers
- `src/regimes/` — regime classifier logic
- `src/features/` — feature computation
- `src/market/` — market data hub / websocket helpers / derived views

### Review / reporting
- `src/review/ingestion.py` — row-level canonicalization
- `src/review/aggregator.py` — history aggregation
- `src/review/performance.py` — normalized performance schema
- `src/review/report.py` — review interpretation and summary building
- `src/review/export.py` — JSON/Markdown export
- `src/runners/weekly_review.py`
- `src/runners/monthly_review.py`
- `src/runners/quarterly_review.py`

### Research / replay
- `src/research/` — offline dataset building, replay helpers, evaluators, reporting, parameter-search scaffolding
- `src/runners/backtest_research.py` — snapshot-based offline research runner

## Current execution architecture reality

### Already true
- shared market/regime detection exists
- all strategy plans can now be generated in parallel
- a parallel execution-cycle path now exists in code
- daemon/artifact flow has started moving onto the parallel-cycle model

### Still transitional
- review/reporting still contains earlier single-route assumptions in places
- historical replay is still snapshot-based, not raw-market replay yet
- some docs and downstream consumers still reflect the older router-composite-centric model

## Recommended reading order for work on this repo

1. `docs/README.md`
2. `project-status.md`
3. `TODO.md`
4. `multi-account-parallel-execution.md`
5. `research-runtime-separation.md`
6. `parameter-promotion-workflow.md`
7. `known-gaps-and-boundaries.md`
8. relevant code modules

## Project continuity rule

Project-local handoff files are no longer the continuity layer here.
Continuity belongs in the workspace memory system; the repo should keep current docs, code, tests, and durable artifact conventions only.

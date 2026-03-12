# Project Map

This document is a high-level orientation map for the rebuilt crypto-trading project.

## Main areas

### Runtime / execution

- `src/runners/execution_cycle.py` — execution artifact writer entrypoint
- `src/runners/minute_engine.py` — runtime loop layer
- `src/runners/realtime_engine.py` — realtime execution-related runner layer
- `src/runners/regime_runner.py` — regime decision runner layer
- `src/runners/shock_monitor.py` — event/shock monitoring layer

### Review / reporting

- `src/review/ingestion.py` — row-level canonicalization of performance hints
- `src/review/aggregator.py` — history aggregation
- `src/review/performance.py` — normalized account snapshot schema
- `src/review/report.py` — report interpretation / sections / actions / narratives
- `src/review/export.py` — JSON + Markdown export
- `src/runners/weekly_review.py` — weekly review runner
- `src/runners/monthly_review.py` — monthly review runner
- `src/runners/quarterly_review.py` — quarterly review runner

### Reports / artifacts

- `logs/runtime/` — execution artifacts
- `reports/trade-review/` — exported review artifacts

## Core docs

- `docs/runtime-and-modes.md`
- `docs/state-and-artifacts.md`
- `docs/execution-artifacts.md`
- `docs/review-architecture.md`
- `docs/review-operations.md`
- `docs/review-automation.md`
- `docs/router-composite.md`

## Reading order for new sessions or handoff

Recommended order:

1. `CURRENT_STATE.md`
2. `README.md`
3. `docs/project-status.md`
4. `docs/project-map.md`
5. `docs/known-gaps-and-boundaries.md`
6. `docs/runtime-and-modes.md`
7. `docs/execution-artifacts.md`
8. `docs/review-architecture.md`
9. relevant runner/report files

## Meta-work principle

For this project, a feature is not considered fully integrated until it has:

- a code entrypoint
- tests
- artifact/path conventions if it persists outputs
- at least one documentation anchor in `docs/`
- enough explanation that a later session can resume without re-deriving intent from code alone

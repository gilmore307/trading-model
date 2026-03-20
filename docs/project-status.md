# Project Status

_Last updated: 2026-03-20_

## Goal

Build a crypto-trading system that:
- runs all strategy accounts in parallel
- keeps historical validation and live runtime operationally separate
- lets historical parameter/research work feed live runtime through explicit publish/activate/rollback workflow
- remains auditable through persisted artifacts, tests, and current docs under `docs/`

## Current state

The project is now in a **transitional but materially real** state:

1. **Runtime / mode system exists**
2. **Execution / state / reconcile layer exists**
3. **Execution artifacts and review pipeline exist**
4. **Snapshot-based offline research exists**
5. **Parallel multi-account execution has started landing**
6. **Project docs have been consolidated under `docs/`**

## What is already real

### Runtime and execution
- `trade_daemon` is a real running daemon path.
- runtime modes and mode policy exist and matter.
- execution submission / verify / reconcile / recovery paths exist as real code.
- route freeze / re-enable mechanics exist.
- execution anomaly handling has been tightened around:
  - missed entry cleanup
  - forced-exit recovery
  - excluding bad execution paths from strategy stats
- execution confirmation now distinguishes stronger evidence levels:
  - trade-confirmed
  - trade-ids-confirmed
  - position-confirmed

### Parallel execution direction
- the earlier single-route-only model is no longer the target.
- all strategy accounts are intended to run simultaneously.
- `build_parallel_plans(...)` exists.
- `run_cycle_parallel()` now exists.
- daemon/artifact flow has started moving onto the parallel-cycle path.

### Review and reporting
- weekly/monthly/quarterly review runners exist.
- execution artifacts are persisted under `logs/runtime/`.
- review export/index plumbing exists.
- execution-quality reporting now includes confirmation-quality distinctions and excluded-trade tracking.

### Research / replay
- `src/research/` exists and is substantial.
- `src/runners/backtest_research.py` provides snapshot-based offline research from historical snapshot JSONL.
- research outputs already cover:
  - regime quality
  - separability
  - strategy × regime matrix
  - strategy ranking
  - parameter-search preview

### Documentation / structure
- project Markdown now lives under `docs/` only.
- root-level project handoff clutter was removed.
- project-local session handoff is no longer part of the intended repo structure.

## What changed recently

### Cleanup / structure cleanup
- removed root-level `SESSION_HANDOFF_*` files from the project
- removed retired closeout clutter and old backup clutter from the repo
- moved project Markdown into `docs/`
- moved loose root scripts into `scripts/`

### Runtime / execution hardening
- `reconcile_mismatch` now still participates in alignment
- entry ledger records real executed size rather than only abstract plan size
- exit verification timeout marks `forced_exit_recovery` and excludes the trade from strategy stats
- missed-entry cleanup now fully clears local execution state and reenables the route
- execution artifacts expose verification quality details

### Live operations
- runtime is under systemd via `crypto-trading.service`
- a real demo-account anomaly on `trend / BTC-USDT-SWAP` was investigated and manually cleaned up
- that anomaly pointed to execution-environment contamination risk between dry-run style state and live trade state

## Current boundaries

### True today
- this is a real development/demo trading system, not just a scaffold
- review and research are real enough to guide engineering work
- parallel execution is now partially implemented in runtime code

### Not finished yet
- full multi-account productionized live cycle is not fully hardened yet
- review/reporting still contains older single-route assumptions in places
- historical replay is still snapshot-based, not raw-market replay
- parameter promotion workflow is documented but not fully productionized end-to-end
- execution environment isolation still needs tightening to prevent dry-run-style state contamination

## Most important next steps

1. harden multi-account parallel live execution
2. isolate dry-run/test/live state and artifact paths more strictly
3. finish review/report migration to true multi-account parallel semantics
4. build raw historical market replay builder
5. complete parameter candidate -> active live parameter promotion path

## Validation snapshot

Recent focused validation for new execution/recovery/parallel changes passed in targeted suites during this work session.
Use `./.venv/bin/python -m pytest -q` for a fresh full-project verification pass after the current reorganization settles.

## Canonical working TODO

Use `docs/TODO.md` as the current task list.

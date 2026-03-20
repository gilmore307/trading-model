# TODO

_Last updated: 2026-03-20_

This is the canonical current task list for the project.

## P0 — immediate cleanup / hardening

- [ ] harden **dry-run / test / live** state isolation
  - split state/artifact paths or otherwise make contamination impossible
  - ensure dry-run adapters cannot write misleading live-trade state
- [ ] verify the new parallel daemon path for several cycles after cleanup
  - confirm no fresh residual local positions appear without real exchange confirmation
- [ ] audit `trend` path after the recent manual forced-exit cleanup and confirm it stays clean

## P1 — multi-account parallel execution

- [x] generate parallel plans for all strategy accounts
- [x] add `run_cycle_parallel()`
- [x] switch daemon/artifact flow onto parallel-cycle path
- [ ] make parallel artifacts the canonical downstream review input
- [ ] remove remaining single-route assumptions from notifier/report glue
- [ ] add clearer per-account parallel cycle summaries

## P1 — historical research / replay

- [x] keep snapshot-based offline research path working
- [ ] design raw historical replay input schema
- [ ] build raw historical market replay runner
- [ ] use the same strategy logic with simulated execution backend
- [ ] support weekly/monthly/quarterly segmented review on historical replay

## P1 — parameter workflow

- [x] document candidate -> publish -> activate -> rollback workflow
- [ ] implement active live parameter override loading in runtime settings
- [ ] emit parameter candidate artifacts from research/replay runs
- [ ] add promotion script for candidate -> active live parameters
- [ ] add rollback script and activation history

## P1 — execution integrity

- [x] exclude missed-entry and forced-exit recovery trades from strategy stats
- [x] record stronger verification evidence in execution artifacts
- [ ] push trade IDs / fill IDs deeper into canonical attribution
- [ ] add better automated repair/rebuild tools for bad local ledger state
- [ ] improve recovery scripts for real anomaly handling

## P2 — review/report migration

- [ ] make weekly review truly compare all parallel live accounts
- [ ] make monthly review support parallel-account comparison and parameter discussion
- [ ] make quarterly review focus on structure/regime pruning with parallel-account evidence
- [ ] reduce router-composite assumptions where they no longer match the always-on parallel model
- [ ] improve regime explanation / narrative quality in reports

## P2 — accounting semantics

- [ ] harden realized / unrealized / funding semantics
- [ ] harden equity start / end / change semantics across longer windows
- [ ] improve drawdown / account-level review semantics

## P3 — repo / doc hygiene follow-up

- [x] move project Markdown under `docs/`
- [x] remove project-local session handoff clutter
- [x] move loose root scripts under `scripts/`
- [ ] do one full repo-wide doc pass to remove stale wording inherited from the old single-route model
- [ ] run a fresh full test suite after the current refactor/cleanup settles

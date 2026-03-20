# Project Status

_Last updated: 2026-03-20_

## Goal

Build a crypto-trading research system that:
- uses long-span 1-minute historical data as the main driver
- evaluates strategy families in a historical-only phase first
- optimizes each strategy family toward dynamic parameters
- compares family champions before considering later live promotion
- remains auditable through persisted artifacts, tests, and current docs under `docs/`

## Current state

The project is now in a **historical-first transition phase**:

1. runtime / execution code exists
2. review/report machinery exists
3. snapshot-based offline research exists
4. project docs have been consolidated under `docs/`
5. strategy-family research has become the current top-level direction

## What is already real

### Runtime and execution foundation
- `trade_daemon` exists as a real daemon path
- runtime modes and mode policy exist
- execution submission / verify / reconcile / recovery paths exist as real code
- execution anomaly handling was materially improved during this work session
- execution confirmation now distinguishes stronger evidence levels:
  - trade-confirmed
  - trade-ids-confirmed
  - position-confirmed

### Research / replay foundation
- `src/research/` exists and is substantial
- `src/runners/backtest_research.py` provides snapshot-based offline research from historical snapshot JSONL
- research outputs already cover:
  - regime quality
  - separability
  - strategy × regime matrix
  - strategy ranking
  - parameter-search preview

### Documentation / structure
- project Markdown now lives under `docs/` only
- root-level project handoff clutter was removed
- project-local session handoff is no longer part of the intended repo structure
- canonical strategy research docs now exist under `docs/`

## What changed recently

### Cleanup / structure cleanup
- removed root-level `SESSION_HANDOFF_*` files from the project
- removed retired closeout clutter and old backup clutter from the repo
- moved project Markdown into `docs/`
- moved loose root scripts into `scripts/`
- rewrote core docs to reflect current structure and current research direction

### Runtime / execution hardening
- `reconcile_mismatch` now still participates in alignment
- entry ledger records real executed size rather than only abstract plan size
- exit verification timeout marks `forced_exit_recovery` and excludes the trade from strategy stats
- missed-entry cleanup now fully clears local execution state and reenables the route
- execution artifacts expose verification quality details

### Strategy research direction reset
- the older predefined 5-strategy / predefined-state framing is no longer the main research path
- the project is now centered on family-based historical strategy research
- candidate pool is open-ended, not capped
- dynamic-parameter optimization is now the target for every strategy family

## Current boundaries

### True today
- this is a real trading/research codebase, not just a scaffold
- review and research are real enough to guide engineering work
- the repo contains runtime and execution machinery that can be reused later

### Not the current focus
- live-runtime rollout is not the main phase right now
- live-lane count is not the current organizing model
- the historical-only phase takes priority over further live orchestration work

### Not finished yet
- historical replay is still snapshot-based, not raw-market replay
- long-span historical 1-minute data acquisition/buildout is not finished
- family-batched research execution framework is not built yet
- dynamic-parameter family optimization is not implemented yet
- execution environment isolation still needs tightening before later live re-expansion

## Most important next steps

1. acquire long-span 1-minute historical data
2. build family-batched historical research execution
3. define and test candidate strategy families
4. optimize each family toward dynamic parameters
5. compare family champions in weekly review

## Validation snapshot

Recent focused validation for execution/recovery/parallel changes passed in targeted suites during this work session.
Use `./.venv/bin/python -m pytest -q` for fresh validation after the next major implementation step.

## Canonical working TODO

Use `docs/TODO.md` as the current task list.

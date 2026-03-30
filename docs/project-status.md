# Project Status

_Last updated: 2026-03-30_

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

### Project meta-work rule
- `docs/` should now be treated as a continuously updated meta-work layer during active development, not as a closeout-only afterthought
- `projects/ops-dashboard/docs/` was explicitly backfilled because it had fallen behind the detailed standard already present in `projects/crypto-trading/docs/`


### Dashboard / evaluation integration updates
- `unsupervised_market_state_evaluation_v1.json` was expanded so it now formally carries:
  - `cluster_parameter_region_cube`
  - `cluster_family_cube`
  - `cluster_variant_cube`
  - enriched `cluster_separation_summary` rows with best-family / best-variant fields
- the default utility dataset for `src/runners/evaluate_unsupervised_labels.py` was moved to the cross-family dataset `strategy_parameter_utility_dataset_v1.jsonl` instead of an MA-only utility file
- this was done to support dashboard questions like “what is the best trading family / best variant in each cluster?” as first-class payloads rather than front-end approximations
- `projects/ops-dashboard` was restructured into clearer modules:
  - Welcome
  - Historical Backtest
  - Trading Performance
  - Market State Analysis
- Historical Backtest is being turned into the control center for instrument selection, strategy selection, artifact checklist, downloads, and load progress
- current dashboard loading work now includes first-pass incremental reuse behavior for same-instrument family dashboards, while explicitly clearing cache for deselected families
- Trading Performance is being narrowed back to trading/return/routing questions
- cluster/state explanation content is being migrated toward Market State Analysis instead of remaining inside Trading Performance
- Market State Analysis is being treated as anonymized at the module level, while State Explanation is allowed to use a controlled real-market projection instrument


### Research pipeline automation skeleton
- a unified research-pipeline orchestrator now exists for the BTC research chain
- pipeline runs now write manifest/log/state artifacts under `logs/pipeline/`
- rule-based anomaly checking now exists so routine unattended runs can remain machine-only unless escalation is actually needed
- current automation scope covers fetch/build/label/evaluate/export for the current BTC + MA + Donchian + Bollinger + unsupervised path
- scheduler/timer templates now exist under `deploy/systemd/`
- the orchestrator now supports first-pass mtime-based freshness skipping for heavy downstream steps
- richer content-aware dependency handling is still unfinished


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

1. finish Bitget `mark/index` history and generate `basis_proxy` as the long-history derivatives-context backbone alongside OKX candles
2. implement `crypto_market_state_dataset_v1` from OKX bars + Bitget funding + Bitget basis proxy
3. build `ma_parameter_utility_dataset_v1` for offline adaptive-parameter modeling
4. run unsupervised market-state discovery baselines (clustering / HMM)
5. evaluate whether discovered states separate MA family parameter performance well enough to justify dynamic adaptation

## Validation snapshot

Recent focused validation for execution/recovery/parallel changes passed in targeted suites during this work session.
Use `./.venv/bin/python -m pytest -q` for fresh validation after the next major implementation step.

## Canonical working TODO

Use `docs/TODO.md` as the current task list.

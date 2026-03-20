# TODO

_Last updated: 2026-03-20_

This is the canonical current task list for the project.

## P0 — immediate architecture correction

- [ ] harden **dry-run / test / live** state isolation
  - split state/artifact paths or otherwise make contamination impossible
  - ensure dry-run adapters cannot write misleading live-trade state
- [ ] separate the project clearly into:
  - historical-dev plane (5 research lanes, no accounts)
  - live-runtime plane (5 live lanes, own accounts)
- [ ] make sure the two planes do not contaminate each other in state, artifacts, statistics, or execution paths

## P1 — historical-dev rebuild (now the main priority)

- [ ] acquire long-span **1-minute** historical data from OKX for the target study range
- [ ] build a canonical historical data storage layout under the project for replay/research
- [ ] define the batch-experiment framework:
  - run candidates by family
  - keep batch sizes limited for server load
  - compare candidates within a family first
- [ ] build the first historical strategy family registry
- [ ] implement first-wave families:
  - moving average family
  - Donchian / breakout family
  - MACD family
  - Bollinger family
  - RSI family
  - Bias/deviation family
  - range/opening breakout family
  - volatility-breakout family
  - grid family
- [ ] for every family, move from fixed-parameter baseline toward **dynamic-parameter** versions
- [ ] define elimination/dominance rules so weak/covered candidates can be dropped early
- [ ] make weekly review the place where time segments / market-style stitching is performed

## P1 — strategy family research framework

- [x] define the candidate pool as **not capped**
- [x] define the “~20 serious candidates reviewed” milestone as a usability threshold, not a hard cap
- [x] define research by family first, then across family champions
- [ ] add implementation status tracking to each candidate/family in the pool
- [ ] build candidate execution status flow:
  - idea -> specified -> implemented -> backtested -> reviewed -> promoted/rejected

## P1 — live runtime hardening

- [x] generate parallel plans for all strategy accounts
- [x] add `run_cycle_parallel()`
- [x] switch daemon/artifact flow onto parallel-cycle path
- [ ] make parallel artifacts the canonical downstream review input
- [ ] remove remaining single-route assumptions from notifier/report glue
- [ ] verify the new parallel daemon path for several cycles after state-isolation cleanup

## P1 — execution integrity

- [x] exclude missed-entry and forced-exit recovery trades from strategy stats
- [x] record stronger verification evidence in execution artifacts
- [ ] push trade IDs / fill IDs deeper into canonical attribution
- [ ] add better automated repair/rebuild tools for bad local ledger state
- [ ] improve anomaly recovery scripts for real runtime handling

## P2 — review/report migration

- [ ] make weekly review compare family champions and parallel live accounts cleanly
- [ ] keep market-style stitching primarily in weekly review, not in normal runtime
- [ ] make monthly review support family-vs-family and live-vs-historical comparison
- [ ] make quarterly review focus on structural pruning and family retention decisions
- [ ] reduce router-composite assumptions where they no longer match the actual model

## P2 — parameter workflow

- [x] document candidate -> publish -> activate -> rollback workflow
- [ ] implement active live parameter override loading in runtime settings
- [ ] emit parameter candidate artifacts from research/replay runs
- [ ] add promotion script for candidate -> active live parameters
- [ ] add rollback script and activation history

## P2 — future strategic targets

- [ ] classification-prediction strategies
- [ ] reinforcement-learning-enhanced strategies

## P3 — repo / docs follow-up

- [x] move project Markdown under `docs/`
- [x] remove project-local session handoff clutter
- [x] move loose root scripts under `scripts/`
- [x] add canonical strategy research docs
- [ ] do one more repo-wide doc pass after the historical-dev rebuild starts landing
- [ ] run a fresh broader test pass after the next major implementation step

# TODO

_Last updated: 2026-03-20_

This is the canonical current task list for the project.

## P0 — automation / continuous research pipeline

- [x] add a unified research pipeline orchestrator for the BTC research chain
- [x] add pipeline manifest/log/state output under `logs/pipeline/`
- [x] add rule-based anomaly checks so machine-only runs can self-screen before any agent review
- [x] add scheduler units/timers for unattended 24x7 execution
- [x] add a first-pass dependency-aware incremental rebuild rule set to skip fresh downstream artifacts
- [ ] add agent-escalation hooks only for repeated failures, anomalies, or major result changes
- [x] start building first-pass trading overview artifacts (family summary / equity curves / trade ledger / composite summary)
- [x] extend the automated pipeline from MA-only into first-pass multi-family research datasets (MA + Donchian + Bollinger)

## P1 — historical-only phase reset

- [ ] treat the project as **historical-only** for the current phase
- [ ] stop using the older “10-line model” as the active organizing model
- [ ] keep live-runtime rollout work deferred unless it directly supports later historical-to-live promotion
- [ ] tighten dry-run / test / live isolation anyway so later live work does not inherit bad state assumptions

## P1 — historical data foundation (main priority)

- [ ] acquire long-span **1-minute** historical data from OKX for the target study range
- [ ] build a canonical historical data storage layout under the project
- [x] add scripts/data-style structure for historical data fetch/maintenance work
- [ ] verify exact earliest practical 1-minute history coverage and chunking strategy
- [ ] define local retention/update workflow for minute-level history

## P1 — market-state description (top priority inside research)

- [x] define market-state description as prior to dynamic-parameter selection
- [x] define the first market-state feature inventory
- [x] define the first market-state architecture / dataset-spec layer
- [ ] finish Bitget `mark/index` history and generate `basis_proxy`
- [ ] implement `crypto_market_state_dataset_v1` using OKX bars + Bitget funding + Bitget basis proxy
- [ ] run unsupervised market-state discovery baselines
- [ ] evaluate state usefulness by MA parameter-performance separation
- [ ] build the first `State × Family × Parameter Region` performance cube from the crypto-only dataset

## P1 — strategy family research system

- [x] define the candidate pool as **not capped**
- [x] define the “~20 serious candidates reviewed” milestone as a usability threshold, not a hard cap
- [x] define research by family first, then across family champions
- [x] define dynamic-parameter optimization as the target for every family
- [ ] add implementation status tracking to each candidate/family in the pool
- [ ] build candidate execution status flow:
  - idea -> specified -> implemented -> backtested -> reviewed -> promoted/rejected

## P1 — first-wave family buildout

- [x] build the first historical strategy family registry
- [ ] implement first-wave families:
  - moving average family (baseline runner started)
  - Donchian / breakout family (baseline runner started)
  - Bollinger mean-reversion family (baseline runner started)
  - MACD family
  - Bollinger family
  - RSI family
  - Bias/deviation family
  - range/opening breakout family
  - volatility-breakout family
  - grid family
- [ ] for every family, start with fixed-parameter baselines, then move toward dynamic-parameter versions
- [ ] define elimination/dominance rules so weak/covered candidates can be dropped early
- [ ] define batch sizing rules based on server load

## P1 — historical review workflow

- [ ] make weekly review the canonical place where time-segment / market-style stitching happens
- [ ] compare family champions in weekly review
- [ ] avoid unnecessary continuous market-style stitching in normal non-review workflows
- [ ] prepare monthly/quarterly historical summary extensions after weekly review stabilizes

## P2 — execution/research infrastructure reuse

- [ ] reuse useful runtime/review machinery where it helps historical research
- [ ] keep snapshot-based offline research working as a transitional tool
- [ ] build raw historical market replay runner
- [ ] move historical strategy testing away from dependence on runtime-generated artifacts

## P2 — parameter workflow (later-stage bridge)

- [x] document candidate -> publish -> activate -> rollback workflow
- [ ] keep this workflow documented but secondary until historical family research yields strong candidates
- [ ] later implement active live parameter override loading in runtime settings
- [ ] later emit parameter candidate artifacts from research/replay runs
- [ ] later add promotion script / rollback script / activation history

## P2 — future strategic targets

- [ ] classification-prediction strategies
- [ ] reinforcement-learning-enhanced strategies

## P3 — repo / docs follow-up

- [x] move project Markdown under `docs/`
- [x] remove project-local session handoff clutter
- [x] move loose root scripts under `scripts/`
- [x] add canonical strategy research docs
- [ ] do one more repo-wide doc pass after the historical-data / family-research buildout starts landing
- [ ] run a fresh broader test pass after the next major implementation step
- [ ] finish validating the family-variant artifact builder after switching retention policy to `all tested summary + top 3 per cluster full artifact`
- [ ] begin migrating canonical time-series datasets toward aligned UTC monthly partitions (`docs/TIME_SERIES_PARTITION_POLICY.md`)

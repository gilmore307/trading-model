# 01 Overview

`trading-model` is the historical research, feature/model development, and promotion-candidate upstream for the trading system.

Its job is to:
- consume upstream market/context data from `trading-data`
- consume upstream strategy execution outputs from `trading-strategy`
- build research-ready data products
- study market state / regime descriptions
- build selector/model layers over the strategy-result surface
- compare modeled outputs against Oracle ceilings and strong baselines
- produce model / parameter outputs that may later be promoted downstream

It should **not** be the canonical home for:
- upstream market-data acquisition and source-adapter ownership
- ETF holdings extraction / refresh workflows
- long-running realtime daemon ownership or live execution operations

Those responsibilities belong in `trading-data` and `quantitative-trading`.

## Upstream / downstream split

### Upstream data layer: `trading-data`
Owns:
- upstream market-data acquisition
- source adapters and refresh workflows
- context acquisition such as ETF holdings extraction
- monthly market-tape and context handoff artifacts

### Upstream research/modeling layer: `trading-model`
Owns:
- research-side dataset construction and curation
- feature engineering for research
- market-state datasets and description frameworks
- strategy family research and backtesting
- promotion candidates and research artifacts

### Downstream runtime layer: `quantitative-trading`
Owns:
- live trade daemon
- active strategy pointer consumption
- realtime execution
- live execution artifacts
- execution-fidelity review and runtime health

## Repository direction

This repo was split out of the older hybrid `crypto-trading` codebase.
The current cleanup direction is:
- keep only trading-model / historical-research responsibilities here
- treat `trading-data` as the canonical upstream acquisition boundary
- remove or retire live-runtime ownership from this repo over time
- align the docs tree to a numbered, ordered reading path
- keep scripts/code grouped under `src/`
- centralize project data management under `data/`

## Main working areas

- `docs/` — project documentation
- `src/research/` — research/backtest logic
- `src/features/` — feature engineering
- `src/regimes/` — regime / market-state modeling
- `src/strategies/` — strategy-family logic
- `src/pipeline/` — research pipeline orchestration
- `data/` — centrally managed project research datasets and manifests

## Current cleanup goals

1. finish separating research/modeling concerns from acquisition and realtime concerns
2. normalize docs into ordered numbered references
3. move remaining script entrypoints toward organized `src/` ownership
4. make `data/` the obvious central research-data boundary
5. keep the repo as the canonical upstream for downstream strategy promotion

## Current modeling direction to preserve

At the current design stage, this repository should explicitly preserve the following research/modeling line:

1. build and maintain candidate strategy families / variants
2. evaluate variants on historical data
3. produce both single-variant and composite comparison outputs
4. treat regime / market-state modeling as a selector layer above the variant pool
5. distinguish between theoretical upper-bound selection and executable state-conditional selection

### Required composite outputs

The modeling line should preserve at least these two composite concepts:

- **oracle composite**
  - hindsight / upper-bound composite
  - for each evaluation segment, chooses the best-performing candidate variant after the fact
  - used as a theoretical ceiling / benchmark
  - not treated as directly executable live logic

- **regime composite**
  - executable composite
  - uses current regime / market-state recognition to choose the preferred variant for the detected state
  - used as the actual forward-usable composite definition
  - should be compared against both the oracle composite and strong single-variant baselines

### Why both composites matter

These two outputs are required because they answer different questions:

- oracle composite: how much value exists in state-aware switching in theory?
- regime composite: how much of that value can the regime model actually capture?

The gap between them is a primary signal for improving regime / market-state modeling.

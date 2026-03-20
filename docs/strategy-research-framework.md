# Strategy Research Framework

_Last updated: 2026-03-20_

## Core direction

The project is no longer centered on keeping the older 5 predefined strategy/regime pairings as the main research path.

The new research direction is:
- build a large candidate pool of strategy families
- test them one by one on long-span 1-minute market history
- optimize each strategy family toward **dynamic parameters** rather than only fixed parameters
- compare the best dynamic version from each family against other families
- identify which families are actually useful, which are fully covered by others, and which deserve promotion into live runtime

## Two independent planes

There should be **10 independent lines** overall.

### Historical-dev plane (5 lines)
- 5 strategy-development lanes
- no exchange accounts required
- simulated execution only
- driven by historical 1-minute market data
- used to discover and improve strategies before live deployment

### Live-runtime plane (5 lines)
- 5 live strategy lanes
- each strategy/account runs in its own account
- exchange execution path
- used for actual live/demo operation

These two planes must not contaminate each other:
- separate state
- separate artifacts
- separate statistics
- separate execution paths

Cross-plane stitching should happen mainly in **weekly review**, not constantly during normal runtime.

## Research unit

A strategy should not be treated as only a name such as "MA" or "RSI".

The real research unit is a full strategy system composed of:

1. **signal generation**
2. **filters**
3. **position sizing / capital management**
4. **exit logic**

## Family-first workflow

Research should be done **by strategy family**, not by mixing all strategies together in one noisy batch.

### Within each family
1. build baseline fixed-parameter variants
2. identify viable parameter ranges
3. move quickly toward **dynamic-parameter versions**
4. eliminate weak/covered variants
5. keep the best family representative

### Across families
After a family champion exists for each major family, compare:
- return
- drawdown
- stability
- time-segment performance
- whether a family is dominated/covered by another family

## Dynamic-parameter target

For every family, the real target is not merely:
- “best fixed parameter set”

The real target is:
- “best dynamic parameter logic for this family”

Examples:
- MA family: faster/slower windows depending on volatility/trend conditions
- breakout family: different window lengths depending on market expansion/compression
- mean-reversion family: different thresholds depending on volatility/state context
- grid family: different spacing or disable rules depending on directional stress

Static parameters are baseline probes, not the final destination.

## Candidate pool rule

The candidate pool is **not capped**.

However:
- concurrent experiments should be batched carefully for server load reasons
- batches should usually contain strategies from the same family
- a first meaningful milestone is around **20 seriously tested candidates/family variants**, after which the framework should already become usable enough to start combining historical and live work more actively

That milestone is **not** a ceiling.

## Exclusions for now

The following are intentionally not first-wave priorities for the current single-market historical buildout:
- cross-exchange arbitrage
- cash-and-carry / spot-futures basis arbitrage
- funding-rate arbitrage

These are not rejected forever, but they are not first-wave targets.

## Target capabilities kept for later

The following remain strategic goals:
- classification-prediction strategies
- reinforcement-learning-enhanced strategies

These should come later, on top of a strong baseline research and replay framework.

## Data rule

Historical-dev should use the same main market granularity as live runtime.

Current rule:
- live runtime uses **1-minute candles**
- historical-dev must also use **1-minute candles** as the main driver

Higher timeframes such as 1H / 1D may still be useful as auxiliary context or review summaries, but not as the main replay driver.

## Selection and elimination rule

A candidate may be dropped if it is:
- clearly dominated by another candidate
- not materially better on return, drawdown, or stability
- not superior in any identifiable time segment / market phase
- operationally too complex relative to its edge

The goal is not to keep many strategies alive.
The goal is to keep only strategy families that earn their place.

## Near-term implementation meaning

The next historical-dev buildout should focus on:
1. long-span 1-minute data acquisition
2. candidate-family registry
3. family-batched backtest execution
4. dynamic-parameter exploration inside each family
5. weekly review that compares family champions and time-segment strength

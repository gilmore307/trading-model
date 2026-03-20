# Strategy Research Framework

_Last updated: 2026-03-20_

## Current phase

The project is currently in a **historical-only research phase**.

That means:
- do not optimize around live-runtime rollout right now
- do not constrain the work around a fixed number of live lanes
- focus on historical strategy research only
- use long-span 1-minute historical data as the main research driver

The older "10-line model" is not the active model for this phase and should be treated as paused/deferred.

## Core direction

The project is no longer centered on keeping the older 5 predefined strategy/regime pairings as the main research path.

The new research direction is:
- build a large candidate pool of strategy families
- test them one by one on long-span 1-minute market history
- optimize each strategy family toward **dynamic parameters** rather than only fixed parameters
- compare the best dynamic version from each family against other families
- identify which families are actually useful, which are fully covered by others, and which deserve promotion later

## Research scope for this phase

### Historical strategy lines
- not limited to 5
- not capped at a fixed number
- candidate pool is open-ended
- actual concurrent batch size should still respect server load

### Live strategy lines
- not the current focus
- should be treated as deferred until historical research yields stronger candidate families and dynamic-parameter logic

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
- a first meaningful milestone is around **20 seriously tested candidates/family variants**, after which the framework should already become usable enough to support later live work with much stronger priors

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

Current rule:
- historical research uses **1-minute candles** as the main driver
- higher timeframes such as 1H / 1D may still be useful as auxiliary context or review summaries, but not as the main replay driver

## Selection and elimination rule

A candidate may be dropped if it is:
- clearly dominated by another candidate
- not materially better on return, drawdown, or stability
- not superior in any identifiable time segment / market phase
- operationally too complex relative to its edge

The goal is not to keep many strategies alive.
The goal is to keep only strategy families that earn their place.

## Near-term implementation meaning

The next historical buildout should focus on:
1. long-span 1-minute data acquisition
2. candidate-family registry
3. family-batched backtest execution
4. dynamic-parameter exploration inside each family
5. weekly review that compares family champions and time-segment strength

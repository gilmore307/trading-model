# 04 Unsupervised Model

This document defines the intended model structure.

## Model objective

The objective is to learn recurring market-state structure from market data itself, without requiring hand-labeled classes and without allowing strategy outcomes to contaminate state definition.

## Core rule

The model must be built in two stages.

### Stage 1 — State discovery
Use only market-side information to define states.

### Stage 2 — Strategy-state mapping
After states are fixed, attach strategy/oracle outcomes to evaluate whether the states are useful.

## Stage 1: state discovery spec

This is the first real model-definition step for the repository.

### Purpose

The state-discovery step should answer:
- can recurring market shapes be discovered from market behavior alone?
- are those shapes stable enough to be treated as reusable states?

### Inputs
From `trading-data` only.

First implementation input scope:
- direct OHLCV or equivalent market bars
- enough continuous history to compute trailing-window market features

No strategy-side fields may enter this step.

## First base-only feature set

The first state-discovery model should use a compact feature set derived only from past-window market behavior.

### A. Return features
- `ret_1`
- `ret_5`
- `ret_15`
- `ret_60`

Meaning:
- trailing return over 1, 5, 15, and 60 base bars

### B. Volatility features
- `rv_5`
- `rv_15`
- `rv_60`

Meaning:
- realized volatility over the trailing 5, 15, and 60 base bars

### C. Range / compression features
- `range_5`
- `range_15`
- `range_60`

Meaning:
- trailing high-low range width normalized by price over the trailing 5, 15, and 60 base bars

### D. Volume / activity features
- `vol_z_5`
- `vol_z_15`
- `vol_z_60`

Meaning:
- relative volume burst / activity z-score over the corresponding trailing windows

### E. Simple directionality features
- `slope_15`
- `slope_60`

Meaning:
- simple price-slope or trend-strength proxy derived only from price over trailing windows

## First feature-set discipline

The first discovery model should stay intentionally small.

Do not include yet:
- derivatives context
- news
- options context
- ETF context
- cross-asset context
- strategy returns
- oracle labels
- variant success statistics

The goal is to test whether the market itself already contains recurring state structure.

## First clustering choice

The first implementation should start with a simple baseline clustering method.

### Recommended first choice
- standardized feature vectors
- KMeans as the first baseline clustering method

Why:
- simple to inspect
- easy to reproduce
- easy to compare across refresh cycles
- good enough as a first falsifiable baseline

### First cluster-count policy

The first pass should not chase an "optimal" cluster count too aggressively.

Instead:
- test a small fixed candidate set such as `k in {4, 6, 8, 10}`
- compare stability and separability diagnostics
- prefer the smallest `k` that yields recurring and interpretable states

## First state-stability diagnostics

The first discovery stage should evaluate stability before any strategy-based usefulness analysis.

### Required diagnostics

#### 1. Cluster size sanity
Check that clusters are not degenerate.
Examples:
- no cluster should dominate nearly everything
- no cluster should have only trivial sample count

#### 2. Reoccurrence over time
Check whether clusters recur across different time segments rather than appearing only in one isolated regime window.

#### 3. Centroid / assignment stability across refreshes
When rerunning on adjacent or rolling datasets, check whether the discovered states remain reasonably similar.

#### 4. Distance / separability sanity
Check whether cluster centers are meaningfully separated in feature space.

#### 5. Transition sanity
Check whether state transitions over time are plausible rather than pure noise flicker.

## Stage-1 output

The state-discovery step should produce:
- a market-only state table keyed by `symbol + ts`
- feature columns used for discovery
- cluster/state assignment
- cluster summary statistics
- stability diagnostics

This is the output that becomes the input to stage 2.

## Stage 2: strategy-state mapping

Once states are fixed, the repository should attach:
- strategy outputs
- oracle outputs
- variant / family identifiers

Then it should answer:
- which variant performs best within each state?
- which parameter region is favored within each state?
- where is the oracle gap especially large?

## Model composite construction principle

The model composite should be built only after the state clusters already exist.

The logic is:
- discover market states from market data alone
- evaluate which variants perform best conditional on each discovered state
- map each state to a preferred variant or policy
- use that mapping to build the model composite

## Primary evaluation principle

The main way to judge model quality is:
- compare the **model composite** against the **oracle composite**

If grouping were perfect, then in theory:
- the model composite could equal the oracle composite

So the main quality question is:
- how much of the oracle composite does the model composite capture?

## Why this is the cleanest design

This design avoids a common failure mode:
- defining states using information that already contains the strategy result

By keeping discovery and evaluation separate, the repository can make a much stronger claim:
- the states are real recurring market structures first
- only afterward do we test whether they are useful for policy selection

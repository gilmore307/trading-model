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
- can we use the descriptive richness of `trading-data` market-side inputs without leaking strategy outcomes into the clustering step?

### Inputs
From `trading-data` only.

This stage may fully use market-side and context-side data from `trading-data`, as long as the information is still purely descriptive of the market and not contaminated by downstream strategy outcomes.

## Stage-1 input hierarchy

### Base market inputs
Always allowed:
- OHLCV / direct market bars
- quotes
- trades

### Market-native enrichment inputs
Allowed in later state-discovery expansions once base-only is established:
- derivatives context
- options context
- news context
- ETF / structural context where the object policy allows it

The rule is not "use as little market data as possible".
The rule is:
- use as much **market-side descriptive information** as is genuinely available from `trading-data`
- but do not use strategy-side performance information during clustering

## First base-only feature set

The first state-discovery model should start with a compact feature set derived only from base market behavior.

### A. Return features
- `ret_1`
- `ret_5`
- `ret_15`
- `ret_60`

### B. Volatility features
- `rv_5`
- `rv_15`
- `rv_60`

### C. Range / compression features
- `range_5`
- `range_15`
- `range_60`

### D. Volume / activity features
- `vol_z_5`
- `vol_z_15`
- `vol_z_60`

### E. Simple directionality features
- `slope_15`
- `slope_60`

## Market-rich discovery expansion order

After base-only v1 is stable, the discovery stage should expand in a deliberate order rather than adding all context at once.

### Expansion 1 — microstructure layer
Add features derived from quotes and trades.

Potential additions:
- spread statistics
- bid/ask imbalance
- trade imbalance
- trade intensity
- short-horizon microstructure volatility proxies

Why first:
These are still very close to direct market behavior and usually improve the model without changing the philosophical boundary.

### Expansion 2 — derivatives-context layer
Add market-descriptive derivatives features where relevant.

Potential additions:
- funding level and change
- basis level and change
- open-interest level and change
- futures/spot pressure proxies

Why second:
These remain market-native signals, but are one step more contextual than pure price/volume behavior.

### Expansion 3 — news/options layer
Add object-native context summaries.

Potential additions:
- recent news intensity
- news surprise proxies
- options implied-vol level
- options skew / put-call structure
- options stress proxies

Why third:
These can be highly informative, but also more sparse, noisier, and more object-dependent.

### Expansion 4 — structural / cross-object context layer
Add ETF / structural context where the object policy allows it.

Potential additions:
- ETF exposure concentration
- constituent ETF context scores
- cross-object context stress indicators
- market-hours-gated structural context fields

Why last:
This is the most policy-sensitive and object-sensitive layer, so it should only be added after the lower-level market-native layers are already understood.

## Discovery-stage purity rule

All of the above expansions are allowed only if they remain market-descriptive.

Still forbidden during clustering:
- strategy returns
- oracle labels
- variant success statistics
- family winner labels
- any downstream policy information

So the discovery stage can become market-rich, but it must remain strategy-blind.

## First clustering choice

The first implementation should start with a simple baseline clustering method.

### Recommended first choice
- standardized feature vectors
- KMeans as the first baseline clustering method

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

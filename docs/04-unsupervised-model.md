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

## Time-causality rule

All discovery features must be computed using past and current market information only.

At time `t`, a feature may use only data from:
- `[t-w+1, t]`

It must not use:
- `t+1` or any later market data
- any future strategy outcome
- any future oracle choice

This guarantees that the discovered state is a true market state, not a result-state.

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

Assume all windows are measured in bar counts.
A practical first setup is:
- short window: `w_s = 3`
- medium window: `w_m = 12`

If the base bar is 5 minutes, this corresponds roughly to:
- short = 15 minutes
- medium = 1 hour

### 0. Single-bar primitives

#### Single-bar log return
- `r_t = log(C_t / C_{t-1})`

#### Single-bar range
- `range_bar_t = (H_t - L_t) / C_t`
- using `C_{t-1}` is also acceptable, but the repository should pick one convention and keep it fixed

#### Single-bar relative volume
- `relvol_t = V_t / (median(V_{t-m:t-1}) + eps)`
- where `m` is a longer baseline window such as `50` or `100`

## Canonical base-only feature family

### A. Return features
- `ret_s`
- `ret_m`

Formula:
- `ret_s(t) = log(C_t / C_{t-w_s})`
- `ret_m(t) = log(C_t / C_{t-w_m})`

### B. Realized volatility features
- `rv_s`
- `rv_m`

Formula:
- `rv_s(t) = sqrt(sum_{i=t-w_s+1}^{t} r_i^2)`
- `rv_m(t) = sqrt(sum_{i=t-w_m+1}^{t} r_i^2)`

Averaged variants are also possible, but the repository should keep one convention fixed.

### C. Range-width features
- `range_s`
- `range_m`

Formula:
- `range_s(t) = (max(H_{t-w_s+1:t}) - min(L_{t-w_s+1:t})) / C_t`
- `range_m(t) = (max(H_{t-w_m+1:t}) - min(L_{t-w_m+1:t})) / C_t`

### D. Relative-activity features
- `activity_s`
- `activity_m`

Formula:
- `volmean_s(t) = mean(V_{t-w_s+1:t})`
- `volmean_m(t) = mean(V_{t-w_m+1:t})`
- choose a longer baseline window `b`, such as `50` or `100`
- `activity_s(t) = volmean_s(t) / (median(V_{t-b:t-1}) + eps)`
- `activity_m(t) = volmean_m(t) / (median(V_{t-b:t-1}) + eps)`

### E. Trend-slope features
- `slope_s`
- `slope_m`

Formula:
- let `y_i = log(C_i)` for the trailing window
- fit a simple OLS regression of `y_i` on time index `i`
- use the slope coefficient as the feature

### F. Directionality features
- `directionality_s`
- `directionality_m`

Formula:
- `directionality_w(t) = abs(log(C_t / C_{t-w})) / (sum_{i=t-w+1}^{t} abs(r_i) + eps)`

Interpretation:
- near `1`: movement is mostly one-directional
- near `0`: there is motion, but it largely cancels out through back-and-forth noise

This feature is especially useful for separating trend-like states from noisy oscillation states.

## Pre-clustering preprocessing

Raw features should not be sent directly into clustering.
For fat-tail market data, first-pass preprocessing should be robust.

### Step 1 — winsorize / clip
Clip each feature using training-window quantiles.

Recommended first policy:
- lower bound = 1st percentile
- upper bound = 99th percentile

A stricter variant like 2nd / 98th percentile is also acceptable, but the choice should be fixed per experiment.

### Step 2 — robust scaling
After clipping, apply robust scaling per feature:

- `z_i(t) = (f_i(t) - median(f_i)) / (IQR(f_i) + eps)`

Where:
- `median(f_i)` and `IQR(f_i)` are computed on the training / fit window only
- `IQR = Q3 - Q1`
- `eps` is a small stabilizer to avoid division by zero

### Why robust scaling

This is preferred over ordinary mean/std scaling for early market-state discovery because:
- market features are often fat-tailed
- extreme moves can distort mean/std normalization
- median/IQR scaling is usually more stable for clustering

So the clustering input is not the raw `x_t`, but the processed feature vector `x_t_tilde` after clipping and robust scaling.

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

### Expansion 2 — derivatives-context layer
Add market-descriptive derivatives features where relevant.

Potential additions:
- funding level and change
- basis level and change
- open-interest level and change
- futures/spot pressure proxies

### Expansion 3 — news/options layer
Add object-native context summaries.

Potential additions:
- recent news intensity
- news surprise proxies
- options implied-vol level
- options skew / put-call structure
- options stress proxies

### Expansion 4 — structural / cross-object context layer
Add ETF / structural context where the object policy allows it.

Potential additions:
- ETF exposure concentration
- constituent ETF context scores
- cross-object context stress indicators
- market-hours-gated structural context fields

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
- robustly processed feature vectors
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
- processed feature vectors used for clustering
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

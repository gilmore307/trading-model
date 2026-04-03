# 04 Unsupervised Model

This document defines **stage 1: market-state discovery**.

## Objective

Discover recurring market-state structure from market data itself, without requiring hand-labeled classes and without allowing strategy outcomes to contaminate state definition.

## Hard boundary

Stage 1 may use market-descriptive information from `trading-data`, but it must not use:
- strategy returns
- oracle labels
- variant success statistics
- any downstream policy information

## Time-causality rule

At time `t`, every discovery feature may use only data from:
- `[t-w+1, t]`

It must not use future market data or future strategy/oracle outcomes.

## Stage-1 input hierarchy

### Base market inputs
Always allowed:
- OHLCV / direct market bars
- quotes
- trades

### Market-native enrichment inputs
Allowed only in later discovery expansions:
- derivatives context
- options context
- news context
- ETF / structural context where the object policy allows it

## First base-only feature set

Assume all windows are measured in bar counts.
A practical first setup is:
- short window: `w_s = 3`
- medium window: `w_m = 12`

### Single-bar primitives
- `r_t = log(C_t / C_{t-1})`
- `range_bar_t = (H_t - L_t) / C_t`
- `relvol_t = V_t / (median(V_{t-m:t-1}) + eps)`

### Canonical base-only feature family

#### Return features
- `ret_s(t) = log(C_t / C_{t-w_s})`
- `ret_m(t) = log(C_t / C_{t-w_m})`

#### Realized-volatility features
- `rv_s(t) = sqrt(sum_{i=t-w_s+1}^{t} r_i^2)`
- `rv_m(t) = sqrt(sum_{i=t-w_m+1}^{t} r_i^2)`

#### Range-width features
- `range_s(t) = (max(H_{t-w_s+1:t}) - min(L_{t-w_s+1:t})) / C_t`
- `range_m(t) = (max(H_{t-w_m+1:t}) - min(L_{t-w_m+1:t})) / C_t`

#### Relative-activity features
- `activity_s(t) = volmean_s(t) / (median(V_{t-b:t-1}) + eps)`
- `activity_m(t) = volmean_m(t) / (median(V_{t-b:t-1}) + eps)`

#### Trend-slope features
- `slope_s`
- `slope_m`

Computed as the OLS slope of log price on time index over the trailing window.

#### Directionality features
- `directionality_w(t) = abs(log(C_t / C_{t-w})) / (sum_{i=t-w+1}^{t} abs(r_i) + eps)`

Interpretation:
- near `1`: movement is mostly one-directional
- near `0`: movement is mostly noisy back-and-forth motion

## Pre-clustering preprocessing

Raw features should not be sent directly into clustering.

### Step 1 — winsorize / clip
Clip each feature using training-window quantiles.

Recommended first policy:
- lower bound = 1st percentile
- upper bound = 99th percentile

### Step 2 — robust scaling
Apply robust scaling per feature:
- `z_i(t) = (f_i(t) - median(f_i)) / (IQR(f_i) + eps)`

Where:
- `median` and `IQR` are computed on the fit window only
- `IQR = Q3 - Q1`

So clustering consumes processed vectors, not raw feature values.

## First clustering family

### Primary model
- Gaussian Mixture Model (GMM)

### Baseline model
- KMeans

## Cluster-count selection rule

Do not choose `k` using only silhouette.

### Candidate set
- `k in {4, 6, 8, 10, 12}`

### Selection criteria
Evaluate for each `k`:
1. geometry / separability
2. cluster size sanity
3. recurrence and temporal stability
4. downstream separation after stage 2 attachment

### Practical rule
Choose the **smallest** `k` that already yields stable and useful state separation.

## First state-stability report

The discovery-stage report should prove that discovered states are:
- stable
- recurring
- not random artifacts

### Global summary
- model version
- feature set
- preprocessing policy
- clustering method
- tested `k`
- selected `k`
- training window
- refresh cadence
- overall geometry metrics
- overall stability metrics

### Per-cluster stability card
For each state:
- cluster size percentage
- centroid / profile summary
- recurrence coverage
- average dwell time
- centroid drift across refits
- assignment confidence
- main transition neighbors

### Temporal panels
- state prevalence by month
- dwell-time distribution by state
- transition matrix
- state recurrence heatmap
- old-vs-new state matching matrix

### Perturbation / resampling stability
- bootstrap consistency
- subsample consistency
- centroid variance
- assignment agreement
- posterior sharpness / uncertainty mass for GMM

### Core stability metrics to watch
1. cluster size distribution
2. centroid separation
3. recurrence coverage
4. average dwell time
5. transition concentration
6. refit matching score
7. assignment confidence / entropy

## Discovery expansion order

After base-only v1 is stable, expand in this order:
1. microstructure features
2. derivatives-context features
3. news/options features
4. structural / cross-object context features

## Stage-1 output

Stage 1 should produce:
- a market-only state table keyed by `symbol + ts`
- feature columns used for discovery
- processed feature vectors used for clustering
- cluster/state assignment
- cluster summary statistics
- model-selection summary across candidate `k`
- stability report

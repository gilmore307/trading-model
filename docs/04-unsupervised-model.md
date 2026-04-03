# 04 Unsupervised Model

This document defines the intended model structure.

## Model objective

The objective is to learn recurring market-state structure from upstream data without requiring hand-labeled state classes in advance.

The model should discover states first, then test whether those states are useful for separating strategy behavior.

## Core modeling principle

The model must support **layered dependency and graceful degradation**.

That means:
- the model should run on the base market layer alone when needed
- optional enrichment/context layers should improve the model when available
- missing optional layers should reduce richness, not break the entire model

## Layer policy matrix

### Layer definitions

- **Base market layer**
  - direct market data required to describe the object itself
- **Direct enrichment layer**
  - object-native enrichments such as derivatives/news/options where relevant
- **Cross-object context layer**
  - context imported from related objects such as ETF context for a stock or crypto object
- **Strategy behavior layer**
  - outputs from `trading-strategy`, required for usefulness evaluation

### Policy by research-object type

#### 1. Stock objects

**Required**
- base market layer
- strategy behavior layer

**Default enabled**
- direct enrichment layer
- ETF context layer

**Optional**
- broader cross-asset context

#### 2. ETF objects

**Required**
- base market layer
- strategy behavior layer

**Default enabled**
- direct enrichment layer

**Optional**
- macro / cross-asset context

**Not primary**
- ETF -> ETF self-context recursion

#### 3. Crypto objects

**Required**
- base market layer
- strategy behavior layer

**Default enabled**
- direct enrichment layer

**Conditionally enabled**
- ETF / ETF-options context during relevant stock-market hours

**Must remain runnable without**
- stock / ETF context outside stock-market hours

## First base-only model spec

This is the minimum viable model path.
It should work before any optional enrichment or context layers are added.

### Purpose

The base-only model should answer:
- can the repository discover useful state structure using only direct market behavior plus strategy outputs?
- can the model composite approach the oracle composite using only base-layer grouping?

### Required inputs

#### From `trading-data`
Base market layer only:
- OHLCV or equivalent direct market rows
- enough continuous history to compute derived base features

#### From `trading-strategy`
Required evaluation side:
- variant-level outputs
- forward-return or equivalent outcome fields
- family/variant identifiers
- oracle outputs for comparison

### Canonical feature family for base-only v1

The first base-only model should start with a compact feature family derived only from direct market behavior:
- short-horizon returns
- medium-horizon returns
- short realized volatility
- medium realized volatility
- short range width
- medium range width
- volume burst / relative activity
- simple trend slope / directionality from price only

The key design rule is:
- no derivatives context
- no news
- no options context
- no ETF context
- no cross-asset context

### Canonical output of base-only v1

The first model should produce:
- a state vector per canonical timestamp
- an unsupervised state assignment or cluster id
- a cluster-conditioned strategy-selection rule
- a **model composite** built from the model's state-conditioned variant selection
- a comparison against the **oracle composite**

## Primary evaluation principle

The main way to judge model quality is:
- compare the **model composite** against the **oracle composite**

### Oracle composite
The oracle composite is the theoretical upper bound.
It chooses the best variant after the fact for each decision segment or evaluation unit.

### Model composite
The model composite is the executable state-conditioned composite.
It chooses variants using the model's discovered states and the learned mapping from state to preferred strategy behavior.

## Main interpretation rule

If the grouping is perfect, then in theory:
- the model composite can equal the oracle composite

In practice, the central model question is:
- how much of the oracle composite does the model composite capture?

That gap is the main quality signal for the model.

### Evaluation criteria for base-only v1

The first base-only model is successful if it can show at least some of the following:
- discovered states are stable enough to recur
- discovered states show different strategy behavior
- the model composite meaningfully improves over strong fixed baselines
- the model composite closes a non-trivial share of the gap to the oracle composite

### Why base-only matters

The base-only model is the anchor.
If it does not work, richer context layers will only hide the problem.

Optional layers should be treated as improvements on top of a working base-only model, not as a substitute for one.

## Full model layers

### 1. Base market layer
Built from `trading-data`.
This is the minimum required descriptive layer.

### 2. Optional enrichment layer
Built from `trading-data`.
Examples:
- derivatives context
- news
- options context

### 3. Optional cross-object context layer
Built from `trading-data`.
Examples:
- ETF context for stocks
- conditional ETF context for crypto during relevant market hours

### 4. Strategy behavior layer
Built from `trading-strategy`.
This layer is used both for usefulness evaluation and for building the model composite mapping.

### 5. Alignment layer
Built inside `trading-model`.
This joins the market/context side and strategy side into one modeling-ready table.

### 6. Unsupervised state model
Built inside `trading-model`.
This is the actual clustering / representation / unsupervised state-discovery layer.

### 7. Composite evaluation layer
Built inside `trading-model`.
This layer converts discovered states into state-conditioned strategy selection and compares:
- model composite
- oracle composite
- strong fixed baselines

## First implementation target

The first model should be built on top of the canonical aligned learning table defined in `03-inputs-and-data-contracts.md`.

The first version should explicitly record which layers were present so later evaluation can answer:
- did optional layers actually improve composite quality?
- which layers matter for which object types?
- does the base-layer-only model remain usable?

## What “unsupervised” means here

It means:
- we do not predefine the final state classes by hand
- we first let the data reveal clusters / state structure
- we then evaluate the usefulness of those discovered states against strategy behavior and composite quality

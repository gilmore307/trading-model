# 04 Unsupervised Model

This document defines the intended model structure.

## Model objective

The objective is to learn recurring market-state structure from upstream data without requiring hand-labeled state classes in advance.

The model should discover states first, then test whether those states are useful for separating strategy behavior.

## Model layers

### 1. State input layer
Built from `trading-data`.

This layer contains the descriptive market/context variables used to represent what the market looked like at each time point.

### 2. Strategy behavior layer
Built from `trading-strategy`.

This layer contains strategy outputs used to evaluate whether discovered states are meaningful.

### 3. Alignment layer
Built inside `trading-model`.

This layer joins the market/context side and the strategy-behavior side into one modeling-ready table.

### 4. Unsupervised state model
Built inside `trading-model`.

This is the actual clustering / representation / unsupervised state-discovery layer.

### 5. Usefulness evaluation layer
Built inside `trading-model`.

This layer tests whether discovered states meaningfully separate:
- strategy families
- variants
- parameter regions
- utility surfaces

## What “unsupervised” means here

It means:
- we do not predefine the final state classes by hand
- we first let the data reveal clusters / state structure
- we then evaluate the usefulness of those discovered states against strategy behavior

## What the model should ultimately learn

At a high level, the model should learn:
- which market conditions tend to cluster together
- which clusters are stable and recurring
- which clusters imply different strategy behavior
- which clusters are useful enough to support selector/model logic later

## What the model is not

It is not:
- a hand-written regime taxonomy masquerading as a learned model
- a strategy execution engine
- a raw data ingestion system
- a live runtime decision daemon

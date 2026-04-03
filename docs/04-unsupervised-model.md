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

## Model layers

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
This layer is used to evaluate whether discovered states are meaningful.

### 5. Alignment layer
Built inside `trading-model`.
This joins the market/context side and strategy side into one modeling-ready table.

### 6. Unsupervised state model
Built inside `trading-model`.
This is the actual clustering / representation / unsupervised state-discovery layer.

### 7. Usefulness evaluation layer
Built inside `trading-model`.
This layer tests whether discovered states meaningfully separate:
- strategy families
- variants
- parameter regions
- utility surfaces
- oracle gap versus achievable state-aware selection

## Scenario behavior

### Stock objects
May use the full layered stack.

### ETF objects
Should primarily rely on direct ETF data, with optional external context.

### Crypto objects
Must remain runnable on crypto-native base/enrichment layers even when stock/ETF context is unavailable.

## First implementation target

The first model should be built on top of the canonical aligned learning table defined in `03-inputs-and-data-contracts.md`.

The first version should explicitly record which layers were present so later evaluation can answer:
- did optional layers actually improve separation?
- which layers matter for which object types?

## What “unsupervised” means here

It means:
- we do not predefine the final state classes by hand
- we first let the data reveal clusters / state structure
- we then evaluate the usefulness of those discovered states against strategy behavior

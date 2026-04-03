# 21 Model Module Development Startpoint

_Last updated: 2026-04-03_

This document is the practical MD startpoint for future `trading-model` module development.

## Main assumption going forward

Before new model-module implementation work begins, assume the strategy execution layer already exists in `trading-strategy`.
That means model development should start from the question:

- **how do we consume and model the output surface produced by `trading-strategy`?**

not from the question:

- **how do we re-embed all strategy replay logic inside `trading-model`?**

## Expected upstream inputs

The upstream execution layer should already be able to provide:
- instrument-scoped variant outputs
- family Oracle outputs
- global Oracle outputs
- monthly partitioned result files
- run manifests describing what was written

## Primary tasks for future `trading-model` implementation

### 1. Output ingestion
Build readers/loaders for `trading-strategy` artifacts.

### 2. Selector-learning datasets
Transform strategy-layer outputs into model-facing datasets that answer:
- which variant was best?
- which family was best?
- how stable was that advantage?
- what state/context features explain that choice?

### 3. Oracle gap analysis
Measure the gap between:
- family/global Oracle composites
- model-produced composites
- strong single-variant baselines

### 4. Promotion logic
Decide which family / variant / model-produced composite is worth promoting downstream.

## What should be documented before code starts

Before the next implementation phase in `trading-model`, the MD set should make these things explicit:
- artifact dictionary for consumed `trading-strategy` outputs
- model-facing dataset schema
- family/variant selection target definitions
- Oracle-gap metric definitions
- promotion criteria

## Development principle

For the upcoming model-module phase:
- prefer clarifying the consumed upstream result surface first
- prefer designing selectors and modeling layers second
- avoid silently rebuilding strategy execution ownership in `trading-model`

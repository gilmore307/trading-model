# 05 Optimization Loop

This repository should improve the model continuously as new data arrives.

## Improvement loop

1. new market/context data arrives from `trading-data`
2. new strategy outputs arrive from `trading-strategy`
3. the aligned learning table is refreshed
4. the unsupervised state model is retrained or updated
5. discovered states are re-evaluated against strategy behavior and oracle benchmarks
6. weak features / weak separations are identified
7. the representation or clustering setup is improved

## First optimization rule

Before comparing richer layer stacks, the repository should first stabilize the **base-only model path**.

Order of work:
1. make base-only work
2. verify it produces useful state separation
3. add one optional layer at a time
4. measure whether the new layer actually improves the model

## What should be optimized

The goal is not only to produce clusters.
The goal is to produce clusters that are:
- stable enough to be useful
- interpretable enough to analyze
- different enough to separate strategy behavior
- refreshable as new upstream data accumulates
- robust under missing optional context layers

## Layer-policy optimization

The repository should not assume that every optional layer is always helpful.
It should explicitly test:
- base-only model
- base + direct enrichment
- base + direct enrichment + cross-object context

for each research-object type.

That means the optimization loop should answer:
- which layers actually improve state quality?
- which layers only add noise?
- which layers help stock objects but not crypto objects?
- which layers are only useful during certain market regimes or time windows?

## Evaluation questions

Each refresh cycle should ask:
- are the discovered states stable over time?
- do they still separate family/variant behavior?
- do they still separate parameter-region utility?
- do they help explain the gap between oracle and executable selection?
- which optional layers add real value?
- can the base-layer-only model still run and remain useful?
- do different research-object types need different context-layer policies?

## Success condition

The model is improving if, over time, it gets better at producing state definitions that explain meaningful differences in upstream strategy behavior while remaining usable under partial data availability.

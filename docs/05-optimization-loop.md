# 05 Optimization Loop

This repository should improve the model continuously as new data arrives.

## Improvement loop

1. new market/context data arrives from `trading-data`
2. new strategy outputs arrive from `trading-strategy`
3. the aligned modeling table is refreshed
4. the unsupervised state model is retrained or updated
5. discovered states are re-evaluated against strategy behavior
6. weak features / weak separations are identified
7. the representation or clustering setup is improved

## What should be optimized

The goal is not only to produce clusters.
The goal is to produce clusters that are:
- stable enough to be useful
- interpretable enough to analyze
- different enough to separate strategy behavior
- refreshable as new upstream data accumulates

## Evaluation questions

Each refresh cycle should ask:
- are the discovered states stable over time?
- do they still separate family/variant behavior?
- do they still separate parameter-region utility?
- are some features no longer useful?
- do we need to revise the representation before clustering again?

## Success condition

The model is improving if, over time, it gets better at producing state definitions that explain meaningful differences in upstream strategy behavior.

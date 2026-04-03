# 02 Workflow

This repository should follow the workflow below.

## End-to-end flow

1. identify the research-object type
2. load the correct layered input stack from `trading-data`
3. load strategy-result artifacts from `trading-strategy`
4. align both upstream streams into modeling-ready learning tables
5. build unsupervised market-state representations
6. train or refresh the state model
7. evaluate whether discovered states separate strategy behavior meaningfully
8. update the model as new upstream data arrives
9. publish model artifacts and conclusions for downstream use

## Step 1 — Identify the research-object type

The repository must first know which type of object is being modeled:
- stock
- ETF
- crypto

This matters because each object class has a different valid context stack.

## Step 2 — Load the correct layered input stack from `trading-data`

Inputs should be loaded in layers rather than as one all-or-nothing dependency bundle.

### Base layer
This is the minimum required layer.
Examples:
- bars / candles
- quotes
- trades where available
- direct market-state descriptive inputs

### Enrichment layer
Examples:
- derivatives context
- funding / basis-like context
- options context
- news

### Cross-object / structural context layer
Examples:
- ETF holdings context
- constituent ETF deltas
- cross-asset context

The exact active layers depend on the research-object type.

## Step 3 — Load strategy outputs from `trading-strategy`

Required principle:
`trading-model` must use upstream-produced artifacts from `trading-strategy`.

These should include structured strategy outputs such as:
- variant outputs
- trades
- equity series
- returns series
- monthly summaries
- meta files
- family oracle outputs
- global oracle outputs
- run manifests

## Step 4 — Build modeling-ready learning tables

The market/context side and strategy side must be aligned into a common learning table.

This learning table must preserve which layers were actually available for each row or run.
That way the model can distinguish between:
- base-only rows
- base + enrichment rows
- base + enrichment + cross-object-context rows

## Step 5 — Build unsupervised market-state representations

This stage converts the aligned learning table into a feature/state representation suitable for unsupervised learning.

The representation should be robust to missing optional layers.
Missing higher-layer context should not break the model.

## Step 6 — Train or refresh the state model

The state model should be trained or updated using unsupervised methods.

The repository should support repeated refresh as new upstream data accumulates.

## Step 7 — Evaluate usefulness against strategy outputs

Discovered states are only useful if they help explain or separate strategy behavior.

The model should therefore be evaluated against real `trading-strategy` outputs such as:
- family-level behavior
- variant-level behavior
- parameter-region utility
- oracle gaps and ranking differences across states

## Step 8 — Improvement loop

As new data arrives from `trading-data` and `trading-strategy`, the model should be re-evaluated and improved.

This includes:
- refreshing the aligned learning table
- retraining or refreshing clustering/state definitions
- checking state stability over time
- checking whether strategy separation remains meaningful
- checking whether optional context layers actually add value

## Step 9 — Publish model-side outputs

This repository should publish:
- state-model artifacts
- state labels or cluster mappings
- state usefulness evaluations
- strategy-separation analysis
- conclusions about what should be promoted or studied next

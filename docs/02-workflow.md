# 02 Workflow

This repository should follow the workflow below.

## End-to-end flow

1. receive upstream datasets from `trading-data`
2. receive upstream strategy outputs from `trading-strategy`
3. align both sides into modeling-ready learning tables
4. build unsupervised market-state representations
5. train or refresh the state model
6. evaluate whether discovered states separate strategy behavior meaningfully
7. update the model as new upstream data arrives
8. publish model artifacts and conclusions for downstream use

## Step 1 — Receive data from `trading-data`

Required principle:
`trading-model` must use market/context data that was produced upstream by `trading-data`.

This repo should not treat local ad-hoc fetches as canonical inputs.

## Step 2 — Receive strategy outputs from `trading-strategy`

Required principle:
`trading-model` must use strategy outputs that were produced upstream by `trading-strategy`.

This repo should not reclaim strategy execution ownership.

## Step 3 — Build modeling-ready learning tables

The two upstream streams must be aligned into a common modeling table keyed by time, instrument, and any other necessary dimensions.

The result should support:
- state discovery
- cluster explanation
- strategy-separation analysis
- incremental model refresh

## Step 4 — Build unsupervised market-state representations

This stage converts the aligned learning table into a feature/state representation suitable for unsupervised learning.

The output of this stage should be a state vector per timestamp or decision point.

## Step 5 — Train or refresh the state model

The state model should be trained or updated using unsupervised methods.

The repository should support repeated refresh as new upstream data accumulates.

## Step 6 — Evaluate usefulness against strategy outputs

Discovered states are only useful if they help explain or separate strategy behavior.

The model should therefore be evaluated against `trading-strategy` outputs such as:
- family-level behavior
- variant-level behavior
- parameter-region utility
- ranking differences across states

## Step 7 — Improvement loop

As new data arrives from `trading-data` and `trading-strategy`, the model should be re-evaluated and improved.

This includes:
- retraining or refreshing clustering/state definitions
- checking state stability over time
- checking whether strategy separation remains meaningful
- refining feature construction where needed

## Step 8 — Publish model-side outputs

This repository should publish:
- state-model artifacts
- state labels or cluster mappings
- state usefulness evaluations
- strategy-separation analysis
- conclusions about what should be promoted or studied next

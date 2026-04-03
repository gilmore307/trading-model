# 02 Workflow

This repository should follow the workflow below.

## Two-stage workflow

### Stage 1 — Market state discovery
1. identify the research-object type
2. load the appropriate market-data layers from `trading-data`
3. build market-only state vectors from past-window market behavior
4. run unsupervised clustering on those state vectors
5. test whether the resulting states are recurring and statistically stable

### Stage 2 — Strategy-state mapping
6. load strategy-result artifacts from `trading-strategy`
7. attach strategy and oracle outcomes onto already-discovered states
8. estimate which variants / parameter regions work best conditional on state
9. build a model composite from the state -> policy mapping
10. compare the model composite against oracle composite and fixed baselines

## Stage 1 rule

State discovery must use market-side information only.

That means the clustering step should not directly use:
- strategy returns
- variant performance
- oracle choices
- any label derived from downstream strategy success

## Stage 2 rule

Only after states are discovered may the repository ask:
- which strategies behave well in this state?
- which parameter regions are favored in this state?
- how much oracle value is captured by state-conditioned policy selection?

## Interpretation

This separates two different scientific questions:

### A. Is there recurring unsupervised market structure?
This is a market-state discovery question.

### B. Is the discovered structure useful for choosing strategies?
This is a strategy-state mapping question.

The second question is only valid if the first step remains clean.

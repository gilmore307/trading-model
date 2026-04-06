# 02 Inputs, Workflow, and Boundary

This document defines the input boundary, two-stage workflow, and the current cross-repo ownership rule for `trading-model`.

## Core principle

The repository has two different input moments:

### 1. State discovery inputs
Used only to define market states.
These must come from `trading-data` and must not include strategy outcomes.

### 2. State evaluation / policy inputs
Used only after states are already defined.
These come from `trading-strategy` and are attached later in order to evaluate usefulness.

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

## Active policy

Separate:
- what is allowed in theory
- what is enabled in v1

### Allowed in theory for discovery
Discovery may eventually use all market-descriptive layers from `trading-data`.

### Enabled in v1
- `discovery_policy = base_only_v1`
- enabled layers:
  - base market layer only
- explicitly disabled in v1 discovery:
  - microstructure layer
  - derivatives-context layer
  - news/options layer
  - ETF / structural context layer

## Non-negotiable rule

Canonical inputs must come from upstream repositories:
- `trading-data`
- `trading-strategy`

Do not treat sample files or ad-hoc example payloads as the source of truth.

## Current cross-repo boundary

Cross-repo sequencing, survivor-floor control, rehydration requests, and storage lifecycle decisions belong in `trading-manager`, not here.

Additional boundary rules:
- raw market data storage belongs in `trading-data`, not `trading-model`
- `trading-model` should read prepared upstream data rather than persisting its own `data/raw/*` market stores
- large derived/model-output artifacts should be partitioned in bounded slices (symbol / month / family / variant) rather than allowed to accumulate as oversized monolithic files
- variant retirement should trigger timely cleanup / archive / compaction of model-side artifacts so dead variants do not keep consuming hot storage forever

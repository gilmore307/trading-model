# Workflow

## Purpose

This file defines the intended component workflow for `trading-model`.

## Primary Flow

```text
market data artifact -> market-only features -> state discovery -> state table -> attach strategy results -> evaluate mappings/verdicts
```

## Operating Principles

- Market-state discovery must not use strategy returns, profitability, or strategy performance.
- Strategy results may be attached only after market states already exist.
- Research outputs need manifests and ready signals before downstream promotion.
- Shared fields, statuses, type values, helpers, and reusable templates must come from `trading-main`.
- Runtime outputs must be written outside Git-tracked source paths.
- Cross-repository handoffs should use accepted request, artifact, manifest, and ready-signal contracts.

## Collaboration Boundary

`trading-model` collaborates with other trading repositories through explicit contracts, not direct mutation of their local state.

Upstream inputs and downstream outputs should be described by artifact references, manifests, ready signals, requests, or accepted storage contracts.

## Open Gaps

- Exact first implementation slice.
- Exact request shape consumed or produced by this repository.
- Exact artifact, manifest, and ready-signal schema interactions.
- Exact shared storage paths and references.
- Exact test harness and fixture policy.
- Exact package/source layout once implementation begins.

# 03 Inputs and Data Contracts

This document defines the current input boundary for `trading-model`.

`trading-model` is a consumer of upstream handoffs.
It should work from stable, explicit research-side input contracts rather than assuming ownership of raw acquisition or strategy execution.

## Primary upstreams

### `trading-data`
Provides upstream market/context data for research use.

Expected categories include:
- market-tape partitions
- context datasets and research-side enrichments
- readiness/completion signals where needed

### `trading-strategy`
Provides standardized strategy-run outputs for model-side comparison and learning.

Expected categories include:
- variant-level outputs
- return/equity/trade artifacts
- family/global comparison summaries
- run manifests and metadata

## Core contract rule

`trading-model` should only depend on inputs that are:
- explicit
- reproducible
- versionable or at least auditable
- aligned with the future long-term operating stack

If an input is intellectually attractive but not sustainably available, it should not become a hidden canonical dependency.

## Input class A — market and context data from `trading-data`

Typical inputs from `trading-data` include:
- price/bar history
- quote/trade history where supported
- optional news or options context
- symbol-specific context artifacts
- monthly or partitioned research-ready handoffs

`trading-model` should treat these as the upstream foundation for offline research.

## Input class B — strategy outputs from `trading-strategy`

Typical consumed outputs include:
- trades
- returns
- equity series
- summary/meta files
- family-level and global Oracle-style comparison outputs
- run manifests for lineage and grouping

These outputs are the surface on top of which `trading-model` studies:
- family quality
- variant robustness
- switching value
- selector/model opportunity

## Canonical design constraint

Model scope must be bounded by sustainably available data.

That means canonical model design should prefer inputs that:
- can be acquired reliably
- can be sustained later
- fit the future stock-focused operating stack
- do not rely on fragile or unsustainable enrichments as the only viable path

## Canonical vs optional inputs

### Canonical inputs
Canonical inputs are the stable foundation for the main modeling line.
They should be expected to remain available in the long-term operating system.

Examples:
- bars / price history
- quote/trade-derived structure where sustainably available
- time/session/calendar context
- stable context datasets that fit the upstream stack

### Optional enrichments
Optional enrichments may improve research quality, but should be treated as additive rather than required.
They must be clearly labeled so the main model line does not silently depend on them.

## Research-side validation checklist

Before using an upstream handoff, verify:
- what object/instrument it belongs to
- what period/window it covers
- what schema/version it uses
- whether the data is complete enough for the intended research step
- whether the lineage back to the upstream system is understandable

## Output-side implication

Because `trading-model` consumes upstream contracts rather than owning all raw generation, its own outputs should also be explicit.
That includes:
- research dataset definitions
- feature/state datasets
- candidate/model outputs
- reports that show how conclusions were derived

## Related archived context

Older split-planning, input-coverage, and future-scope notes were moved to `docs/archive/`.
Those files remain useful as historical reasoning context, but they are no longer the main reading path.

# 03 Inputs and Data Contracts

This document defines the required input boundary for `trading-model`.

## Core principle

The repository has two different input moments:

### 1. State discovery inputs
Used only to define market states.
These must come from `trading-data` and must not include strategy outcomes.

### 2. State evaluation / policy inputs
Used only after states are already defined.
These come from `trading-strategy` and are attached later in order to evaluate usefulness.

## Non-negotiable rule

Canonical inputs for this repository must come from upstream repositories:
- `trading-data`
- `trading-strategy`

Do not treat sample files under `data/` or ad-hoc example payloads as the source of truth.
The source of truth is the upstream implementation and its produced artifact formats.

## Stage 1 input rule: state discovery

The state-discovery stage may use **all market-descriptive data** produced by `trading-data`.

That means it may use:
- base market data
- quotes/trades-derived microstructure information
- derivatives context
- news/options context
- ETF / structural context when allowed by object policy

As long as the information still describes the market itself and not downstream strategy success.

This stage must not use:
- strategy returns
- variant ids as labels
- oracle selections
- any downstream strategy-success signal

## Stage 2 input rule: state evaluation and policy mapping

After state clusters are fixed, attach:
- variant-level outputs from `trading-strategy`
- forward returns / utility fields
- oracle outputs
- family / variant metadata

These inputs are for evaluation and policy mapping only.
They must not flow backward into the discovery step.

## Two-table split

### State table
The first canonical state table should be keyed by:
- `symbol`
- `ts`

It contains:
- market-only or market-descriptive state features
- discovered cluster/state assignment
- layer-presence fields for market-side context

### State-evaluation table
After state discovery, attach strategy-side fields by:
- `symbol`
- `ts`
- `family_id`
- `variant_id`

It contains:
- the discovered state id
- strategy / oracle outcomes aligned to that state

## Why the two-table split matters

This split keeps the system honest.

- the **state table** answers: what recurring market shapes exist?
- the **state-evaluation table** answers: what strategy behavior is associated with each discovered state?

That is the cleanest way to avoid leakage.

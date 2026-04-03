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

## Research-object scenarios

### Stock research objects
Potential market-side layers:
- direct stock market data
- stock news and options context
- ETF holdings base snapshots
- per-symbol ETF context records

### ETF research objects
Potential market-side layers:
- direct ETF market/news/options data
- optional non-ETF macro or cross-asset context

### Crypto research objects
Potential market-side layers:
- direct crypto market data
- direct crypto derivatives context
- optional ETF / ETF-options context during stock-market trading hours only

## Stage 1 input rule: state discovery

The state-discovery stage should use only market-side inputs.

### First base-only state-discovery input set
- OHLCV or equivalent direct market rows
- market-derived features computed from past fixed windows

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

## First canonical join contract

### State table
The first canonical state table should be keyed by:
- `symbol`
- `ts`

It contains:
- market-only state features
- discovered cluster/state assignment
- layer-presence fields for market-side context

### State-evaluation table
After state discovery, attach strategy-side fields by:
- `symbol`
- `ts`
- `family_id`
- `variant_id`

This table contains:
- the discovered state id
- the strategy / oracle outcomes aligned to that state

## Why the two-table split matters

This split keeps the system honest.

- the **state table** answers: what recurring market shapes exist?
- the **state-evaluation table** answers: what strategy behavior is associated with each discovered state?

That is the cleanest way to avoid leakage.

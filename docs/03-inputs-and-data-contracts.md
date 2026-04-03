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

## Active policy

Separate:
- what is allowed in theory
- what is enabled in v1

### Allowed in theory for discovery
Discovery may eventually use all market-descriptive layers from `trading-data`, including:
- base market data
- microstructure
- derivatives context
- news/options context
- ETF / structural context where object policy allows it

### Enabled in v1
- `discovery_policy = base_only_v1`
- enabled layers:
  - base market layer only
- explicitly disabled in v1 discovery:
  - microstructure layer
  - derivatives-context layer
  - news/options layer
  - ETF / structural context layer

This makes the current commitment explicit while preserving future capability.

## Non-negotiable rule

Canonical inputs for this repository must come from upstream repositories:
- `trading-data`
- `trading-strategy`

Do not treat sample files under `data/` or ad-hoc example payloads as the source of truth.
The source of truth is the upstream implementation and its produced artifact formats.

## Stage 1 input rule: state discovery

The state-discovery stage may use **all market-descriptive data** produced by `trading-data` in theory, but only the layers enabled by the current discovery policy in practice.

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

## First state-evaluation table shape

The first state-evaluation table should be a long-format table.

### Key fields
- `research_object_type`
- `symbol`
- `ts`
- `timestamp`
- `month`
- `state_id`
- `family_id`
- `variant_id`

### State-side fields copied from the state table
- `state_id`
- `state_confidence` if available
- layer-presence flags
- any minimal state-profile reference needed for downstream grouping

### Strategy-side fields
Use bar-based horizons as the canonical contract:
- `forward_return_1bar`
- `forward_return_3bar`
- `forward_return_12bar`
- `forward_return_24bar`
- `equity`
- `return_since_prev`
- `trade_pnl`
- `position`
- `signal_state` if exposed

### Oracle-side fields
- `family_oracle_selected_variant_id`
- `global_oracle_selected_family_id`
- `global_oracle_selected_variant_id`
- `oracle_forward_return_1bar`
- `oracle_forward_return_3bar`
- `oracle_forward_return_12bar`
- `oracle_forward_return_24bar`
- `oracle_gap_1bar`
- `oracle_gap_3bar`
- `oracle_gap_12bar`
- `oracle_gap_24bar`

Where:
- `oracle_gap_Nbar = oracle_forward_return_Nbar - forward_return_Nbar`

### Lineage fields
- `strategy_run_id`
- `strategy_partition_month`
- `data_partition_month`
- `source_manifest_id`

## Alignment and tolerance rules

The attach step must use explicit rules rather than informal matching.

### Default key
- exact `symbol + ts` match when available

### Allowed fallback
If exact match is unavailable:
- allow previous-bar attach only
- do not allow future-bar attach
- use the most recent row at or before `ts`

### Tolerance rule
The default tolerance for strategy/oracle attach is:
- at most one base-bar interval backward

If no eligible row exists inside tolerance:
- do not fabricate values
- keep strategy/oracle fields null
- mark attach status explicitly

### Attach-failure rule
Attach failure should not silently drop the state row.
Preferred behavior:
- keep the state row
- leave stage-2 fields null for the missing attachment
- record attach status / attach source for auditability

## Output partition rule

Downstream tables generated from these contracts should be partitioned to avoid oversized files.

Default partition dimensions:
- `symbol`
- `family`
- `variant`
- `month`

At minimum:
- state tables should be partitioned by `symbol + month`
- state-evaluation tables should be partitioned by `symbol + family + variant + month`

## Why the two-table split matters

This split keeps the system honest.

- the **state table** answers: what recurring market shapes exist?
- the **state-evaluation table** answers: what strategy behavior is associated with each discovered state?

That is the cleanest way to avoid leakage.

# 03 Inputs and Data Contracts

This document defines the required input boundary for `trading-model` based on the **actual upstream code paths** in `trading-data` and `trading-strategy`.

## Non-negotiable rule

Canonical inputs for this repository must come from upstream repositories:
- `trading-data`
- `trading-strategy`

Do not treat sample files under `data/` or ad-hoc example payloads as the source of truth.
The source of truth is the upstream implementation and its produced artifact formats.

## Upstream A — `trading-data`

### What the code shows

`trading-data` currently owns scripts/modules for producing:
- historical bars
- historical quotes
- historical trades
- news
- options snapshots
- derivatives context from Bitget
- ETF/context holdings outputs

Representative producer entrypoints include:
- `src/data/alpaca/fetch_historical_bars.py`
- `src/data/alpaca/fetch_historical_quotes.py`
- `src/data/alpaca/fetch_historical_trades.py`
- `src/data/alpaca/fetch_news.py`
- `src/data/alpaca/fetch_option_snapshots.py`
- `src/data/bitget/fetch_derivatives_context.py`
- `src/data/okx/fetch_history_candles.py`

### Output pattern

The real pattern in `trading-data` is:
- month-partitioned storage
- JSONL row files for market tape datasets
- companion meta/manifest files in some paths
- context outputs under `context/`

### Canonical input classes from `trading-data`

`trading-model` should be designed to consume these classes when relevant:
- bars / candles
- quotes
- trades
- derivatives context such as funding / basis-like context
- optional context layers such as news / options / ETF context when those are explicitly part of the modeling design

## Upstream B — `trading-strategy`

### What the code shows

`trading-strategy` currently owns:
- family definitions
- variant generation
- backtest/simulation execution
- family and global oracle composites
- partitioned output writing
- run manifests

Representative implementation paths include:
- `src/families/ma.py`
- `src/families/donchian.py`
- `src/families/bollinger.py`
- `src/composites/oracle.py`
- `src/runners/run_partitioned_outputs.py`
- `src/simulation/output_partitioning.py`
- `src/simulation/run_manifest.py`

### Output pattern

The real pattern in `trading-strategy` is that it writes structured run outputs for:
- trades
- equity
- returns
- monthly summaries
- meta
- family oracles
- global oracles
- run manifests

## Required modeling join

The model must be built from a join between:
- market/context state from `trading-data`
- strategy behavior from `trading-strategy`

At minimum, the alignment contract should support joins by:
- instrument / symbol
- timestamp or bar-aligned time key
- partition / month window where needed
- run / family / variant identifiers on the strategy side

## First concrete learning-table contract

The first implementation target in this repository should be a canonical aligned learning table.

### Table purpose

One row should represent:
- a market/context snapshot at time `ts`
- plus the strategy-behavior observations attached to that same point or aligned decision window

### Primary key

Minimum key:
- `symbol`
- `ts`

Optional extensions later:
- `dataset_month`
- `timeframe`
- `run_id`
- `family_id`
- `variant_id`

## Required field groups

### A. Identity fields
From alignment logic:
- `symbol`
- `ts`
- `timestamp`
- `dataset_month`

### B. Market-state descriptive fields
From `trading-data` bars / quotes / trades / derivatives context:
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `return_1m`
- `return_5m`
- `return_15m`
- `return_1h`
- `realized_vol_*`
- `range_width_*`
- `quote_spread_*` where available
- `trade_imbalance_*` where available
- `funding_rate` where available
- `basis_pct` where available

The exact suffix windows may evolve, but the field family should stay explicit.

### C. Optional context fields
From `trading-data` optional context layers when intentionally enabled:
- `news_count_*`
- `options_*`
- `context_*`

These must be clearly marked optional so the base model does not silently depend on them.

### D. Strategy behavior fields
From `trading-strategy` outputs:
- `family_id`
- `variant_id`
- `position`
- `signal_state` if exposed
- `forward_return_*`
- `equity`
- `return_since_prev`
- `trade_pnl` where alignable
- `summary_score` where emitted

### E. Oracle / benchmark fields
From `trading-strategy` composite/oracle outputs:
- `family_oracle_selected_variant_id`
- `global_oracle_selected_family_id`
- `global_oracle_selected_variant_id`
- `oracle_forward_return_*`

These are needed to evaluate whether discovered states capture meaningful switching value.

### F. Lineage fields
From upstream metadata / manifests:
- `strategy_run_id`
- `strategy_partition_month`
- `data_partition_month`
- `source_manifest_id` or equivalent upstream lineage reference

## Join rules

### Base time alignment

The base alignment should be bar-close aligned by `symbol + ts`.

If exact timestamp equality is not available, the fallback rule should be:
- align strategy row to the most recent market/context row at or before the strategy timestamp within a documented tolerance window

### Multi-output strategy alignment

If multiple strategy outputs exist for the same `symbol + ts`, the repository should support either:
- one row per `(symbol, ts, family_id, variant_id)`
- or a base state row plus nested strategy payloads

For the first implementation, the cleaner choice is usually:
- **one row per `(symbol, ts, family_id, variant_id)`**

because it simplifies downstream evaluation.

## First implementation scope

The first concrete implementation should stay narrow.

### Required from `trading-data`
- bars/candles
- derivatives context when available

### Required from `trading-strategy`
- variant outputs
- returns/equity outputs
- family/global oracle outputs
- run manifests

### Deferred until later
- news
- options snapshots
- ETF/context layers not directly tied to the first state model

## Contract discipline

When rebuilding code in this repo, every field in the learning table should be traceable to:
- a specific upstream repo
- a specific upstream artifact type
- a specific alignment rule

If a field cannot be traced upstream, it should not enter the canonical table yet.

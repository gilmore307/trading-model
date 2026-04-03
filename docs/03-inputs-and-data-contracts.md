# 03 Inputs and Data Contracts

This document defines the required input boundary for `trading-model` based on the **actual upstream code paths** in `trading-data` and `trading-strategy`.

## Non-negotiable rule

Canonical inputs for this repository must come from upstream repositories:
- `trading-data`
- `trading-strategy`

Do not treat sample files under `data/` or ad-hoc example payloads as the source of truth.
The source of truth is the upstream implementation and its produced artifact formats.

## Core dependency rule

Inputs must be modeled in layers.

That means:
- some layers are required
- some layers are optional enrichments
- some layers are conditional on research-object type or market hours
- missing optional layers must not make the model unusable

## Research-object scenarios

### Stock research objects
Potential upstream layers:
- direct stock market data
- stock news and options context
- ETF holdings base snapshots
- per-symbol ETF context records

### ETF research objects
Potential upstream layers:
- direct ETF market/news/options data
- optional non-ETF macro or cross-asset context

ETF -> ETF self-context should not be treated as the primary self-context path.

### Crypto research objects
Potential upstream layers:
- direct crypto market data
- direct crypto derivatives context
- optional ETF / ETF-options context during stock-market trading hours only

Outside stock-market trading hours, crypto modeling must be able to run without stock/ETF context.

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

## First concrete learning-table contract

The first implementation target in this repository should be a canonical aligned learning table.

### Table purpose

One row should represent:
- a market/context snapshot at time `ts`
- plus the strategy-behavior observations attached to that same point or aligned decision window
- plus explicit information about which data layers were available

### Primary key

Minimum key:
- `symbol`
- `ts`
- `family_id`
- `variant_id`

## Required field groups

### A. Identity fields
- `research_object_type` (`stock` | `etf` | `crypto`)
- `symbol`
- `ts`
- `timestamp`
- `dataset_month`

### B. Layer-presence fields
These fields make graceful degradation explicit:
- `has_base_market_layer`
- `has_derivatives_layer`
- `has_news_layer`
- `has_options_layer`
- `has_etf_context_layer`
- `has_cross_asset_context_layer`
- `market_hours_context_active`

### C. Base market layer fields
Minimum required descriptive layer, from `trading-data`:
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

This is the minimum layer that must exist for the model to run.

### D. Optional enrichment layer fields
From `trading-data` where available:
- `quote_spread_*`
- `trade_imbalance_*`
- `funding_rate`
- `basis_pct`
- `news_count_*`
- `options_*`

These should enrich the model, not define whether the model is runnable.

### E. Optional structural / cross-object context fields
From `trading-data` where available and relevant:
- `etf_context_*`
- `constituent_etf_delta_*`
- `cross_asset_context_*`

These are optional and scenario-dependent.

### F. Strategy behavior fields
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

### G. Oracle / benchmark fields
From `trading-strategy` composite/oracle outputs:
- `family_oracle_selected_variant_id`
- `global_oracle_selected_family_id`
- `global_oracle_selected_variant_id`
- `oracle_forward_return_*`

### H. Lineage fields
- `strategy_run_id`
- `strategy_partition_month`
- `data_partition_month`
- `source_manifest_id` or equivalent upstream lineage reference

## Join rules

### Base rule
The base alignment should be bar-close aligned by `symbol + ts`.

### Fallback rule
If exact timestamp equality is not available:
- align strategy row to the most recent market/context row at or before the strategy timestamp within a documented tolerance window

### Layer rule
If optional context is missing:
- the row is still valid if the base market layer and strategy layer exist
- missing optional layers must be represented explicitly through the layer-presence fields

## Scenario-specific dependency rules

### Stock
Stocks may use:
- base market layer
- enrichment layer
- ETF context layer

### ETF
ETFs should primarily rely on:
- their own base market layer
- their own enrichment layer
- optional macro/cross-asset context

ETF self-context recursion should not be a required dependency.

### Crypto
Crypto should primarily rely on:
- its own base market layer
- its own derivatives/enrichment layer

ETF/stock context may be used only as a conditional additional layer during relevant market hours.

## First implementation scope

### Required from `trading-data`
- base market layer
- direct derivatives/enrichment where available

### Required from `trading-strategy`
- variant outputs
- returns/equity outputs
- family/global oracle outputs
- run manifests

### Deferred until later
- richer news usage
- richer options usage
- more complex structural context usage

## Contract discipline

When rebuilding code in this repo, every field in the learning table should be traceable to:
- a specific upstream repo
- a specific upstream artifact type
- a specific alignment rule
- a specific dependency layer

If a field cannot be traced upstream, it should not enter the canonical table yet.

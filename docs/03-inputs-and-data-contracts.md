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

This means `trading-model` should expect upstream inputs in terms of:
- partitioned historical market rows
- partitioned context/enrichment rows
- month-level manifests or metadata where available

### Canonical input classes from `trading-data`

`trading-model` should be designed to consume these classes when relevant:
- bars / candles
- quotes
- trades
- derivatives context such as funding / basis-like context
- optional context layers such as news / options / ETF context when those are explicitly part of the modeling design

### Important design rule

`trading-model` should consume these upstream outputs as delivered artifacts.
It should not recreate fetch logic locally.

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

This means `trading-model` should not rely on toy examples under `examples/` as the contract.
It should rely on the real emitted output classes from the strategy runner path.

### Canonical input classes from `trading-strategy`

`trading-model` should be designed to consume:
- variant-level result rows
- family-level summaries
- returns/equity series
- trade ledgers when needed for analysis
- oracle outputs
- run manifests / metadata for lineage

## Required modeling join

The model must be built from a join between:
- market/context state from `trading-data`
- strategy behavior from `trading-strategy`

At minimum, the alignment contract should support joins by:
- instrument / symbol
- timestamp or bar-aligned time key
- partition / month window where needed
- run / family / variant identifiers on the strategy side

## Practical implication for implementation

When rebuilding code in this repo, the first concrete implementation target should be an aligned learning table with fields that can be traced back to:
- a specific upstream `trading-data` artifact class
- a specific upstream `trading-strategy` artifact class

If a field cannot be traced upstream, it should be treated as non-canonical until documented.

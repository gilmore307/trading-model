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

## Field mapping by layer

### 1. Base market layer

**Source repo**
- `trading-data`

**Primary upstream artifact classes**
- bars / candles
- quotes
- trades where available

**First implementation fields**
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `trade_count` where available
- `vwap` where derivable or available
- `return_1m`
- `return_5m`
- `return_15m`
- `return_1h`
- `realized_vol_5m`
- `realized_vol_15m`
- `realized_vol_1h`
- `range_width_5m`
- `range_width_15m`
- `range_width_1h`

**Expected upstream artifact mapping**
- bars/candles JSONL from:
  - `src/data/alpaca/fetch_historical_bars.py`
  - `src/data/okx/fetch_history_candles.py`
- quotes JSONL from:
  - `src/data/alpaca/fetch_historical_quotes.py`
- trades JSONL from:
  - `src/data/alpaca/fetch_historical_trades.py`

**Mapping rule**
- OHLCV fields come directly from bar/candle artifacts
- `quote_volume` comes from upstream quote-volume / quote-notional fields when available
- `trade_count` and `vwap` may come directly from upstream or be derived during alignment if raw trades/quotes are present
- return / realized-vol / range-width fields are derived inside `trading-model` from the aligned base market rows, not fetched as upstream finished features

### 2. Direct enrichment layer

**Source repo**
- `trading-data`

**Primary upstream artifact classes**
- derivatives context
- quotes/trades derived microstructure context
- object-native news
- object-native options snapshots

**First implementation fields**
- `quote_spread_bps`
- `bid_ask_imbalance`
- `trade_imbalance`
- `funding_rate`
- `basis_pct`
- `open_interest` where available
- `news_count_1h`
- `news_count_1d`
- `options_iv_atm` where available
- `options_skew_*` where available
- `options_put_call_*` where available

**Expected upstream artifact mapping**
- derivatives context from:
  - `src/data/bitget/fetch_derivatives_context.py`
- news JSONL from:
  - `src/data/alpaca/fetch_news.py`
- options snapshots JSONL from:
  - `src/data/alpaca/fetch_option_snapshots.py`
- quotes/trades JSONL from:
  - `src/data/alpaca/fetch_historical_quotes.py`
  - `src/data/alpaca/fetch_historical_trades.py`

**Mapping rule**
- `funding_rate`, `basis_pct`, and `open_interest` come from direct derivatives-context artifacts where present
- `quote_spread_bps`, `bid_ask_imbalance`, and `trade_imbalance` are derived inside `trading-model` from quotes/trades data
- news and options fields are aggregated inside `trading-model` from the corresponding upstream raw context artifacts

### 3. Cross-object / structural context layer

**Source repo**
- `trading-data`

**Primary upstream artifact classes**
- ETF holdings base snapshots
- per-symbol ETF context records
- cross-asset context outputs

**First implementation fields**
- `etf_exposure_count`
- `etf_weight_top1`
- `etf_weight_top3_sum`
- `etf_context_direction_score`
- `etf_context_concentration_score`
- `cross_asset_context_score` where available
- `market_hours_context_active`

**Expected upstream artifact mapping**
- ETF holdings outputs from:
  - `src/data/nport/build_monthly_etf_outputs.py`
  - `src/data/nport/build_monthly_output_manifest.py`
- per-symbol ETF context records from:
  - `context/constituent_etf_deltas/<SYMBOL>.md`
- supporting N-PORT lineage from:
  - `src/data/nport/*`

**Mapping rule**
- the first implementation should not consume ETF markdown blobs directly as raw model inputs
- instead, `trading-model` should extract structured context variables from the upstream ETF-context outputs and manifest-supported holdings artifacts
- `market_hours_context_active` should be computed inside `trading-model` based on the object type and active time window policy

### 4. Strategy behavior layer

**Source repo**
- `trading-strategy`

**Primary upstream artifact classes**
- variant outputs
- returns series
- equity series
- summaries
- meta

**First implementation fields**
- `family_id`
- `variant_id`
- `position`
- `signal_state` if exposed
- `forward_return_1bar`
- `forward_return_5bar`
- `forward_return_15bar`
- `forward_return_1h`
- `equity`
- `return_since_prev`
- `trade_pnl` where alignable
- `summary_score` where emitted

**Expected upstream artifact mapping**
- partitioned outputs written by:
  - `src/runners/run_partitioned_outputs.py`
- output partition helpers under:
  - `src/simulation/output_partitioning.py`
- run manifests under:
  - `src/simulation/run_manifest.py`

**Mapping rule**
- variant-level outputs are the primary strategy-side learning rows
- `forward_return_*`, `equity`, and related fields should be taken from or derived from the emitted strategy outputs rather than recomputed from scratch in `trading-model`
- `family_id` and `variant_id` must remain native upstream identifiers, not local aliases

### 5. Oracle / benchmark layer

**Source repo**
- `trading-strategy`

**Primary upstream artifact classes**
- family oracle outputs
- global oracle outputs

**First implementation fields**
- `family_oracle_selected_variant_id`
- `global_oracle_selected_family_id`
- `global_oracle_selected_variant_id`
- `oracle_forward_return_1h`
- `oracle_forward_return_session` where available

**Expected upstream artifact mapping**
- oracle builders and outputs from:
  - `src/composites/oracle.py`
  - `src/runners/run_partitioned_outputs.py`

**Mapping rule**
- oracle fields come from real emitted oracle outputs, not from locally reconstructed hindsight labels unless explicitly documented

### 6. Lineage layer

**Source repos**
- `trading-data`
- `trading-strategy`

**First implementation fields**
- `strategy_run_id`
- `strategy_partition_month`
- `data_partition_month`
- `source_manifest_id`
- `data_source_kind`
- `strategy_source_kind`

**Expected upstream artifact mapping**
- data-side manifest/meta files from `trading-data`
- run manifest/meta files from `trading-strategy`

**Mapping rule**
- every canonical row should be traceable back to upstream artifacts
- if a row has no lineage, it should not be considered canonical

## Alignment policy

This section defines the first hard alignment rules for joining upstream artifacts into the canonical learning table.

### 1. Canonical time axis

The canonical time axis should be the **base market bar close timestamp**.

That means:
- every aligned row is anchored to a market-state timestamp from the base market layer
- strategy outputs and optional context are joined onto that timestamp

### 2. Canonical join order

The first implementation should join in this order:
1. base market layer
2. direct enrichment layer
3. cross-object / structural context layer
4. strategy behavior layer
5. oracle / benchmark layer
6. lineage layer

Reason:
The market-state row is the anchor. Everything else decorates or evaluates that state row.

### 3. Base alignment rule

Default join key:
- `symbol + ts`

If exact equality is available, use exact equality.

### 4. Fallback alignment rule

If exact timestamp equality is not available:
- align an upstream row to the most recent canonical market row with `row_ts <= ts`
- only accept the match if it falls within the allowed tolerance window for that layer

If no valid row is found inside tolerance:
- leave the layer missing
- mark the corresponding `has_*_layer` field as false
- do not fabricate a value

### 5. First tolerance policy by layer

#### Base market layer
- exact timestamp match required within the chosen bar partition
- no fallback because this layer defines the canonical row itself

#### Direct derivatives/context layer
- allow as-of joins
- first default tolerance: **15 minutes** for short-lived market context fields
- if beyond tolerance, mark missing

#### News layer
- do not nearest-neighbor a single article row
- aggregate over explicit backward-looking windows such as:
  - last 1 hour
  - last 1 day
- no nearest-row substitution beyond the aggregation window definition

#### Options layer
- allow as-of joins
- first default tolerance: **same session / same market-hours block**
- if outside the valid market-hours block, mark missing

#### ETF context layer
- treat as slow-moving structural context
- align by active month / active published context period, not by minute-level equality
- within the valid month/context window, the same context may attach to many rows

#### Strategy behavior layer
- prefer exact `symbol + ts` alignment where emitted strategy outputs are already bar-aligned
- if not exact, use the most recent row at or before `ts`
- first default tolerance: **one base-bar interval**

#### Oracle / benchmark layer
- use the same alignment policy as the strategy behavior layer
- oracle rows should map to the same canonical decision timestamp as the corresponding strategy rows

### 6. Window-direction rule

For the first implementation, all non-structural fallback joins should be **backward-looking only**.

That means:
- no future leakage
- no joining to a later row just because it is closer in time

### 7. Aggregation rule

If multiple rows from the same layer fall into one canonical window:
- use an explicit deterministic aggregation rule per field family

Examples:
- counts → sum
- rates / ratios → last valid or weighted mean, depending on field definition
- context snapshots → most recent valid snapshot within tolerance

The aggregation rule must be documented per field family before implementation.

### 8. Missingness rule

Missing optional data must be represented explicitly.

That means:
- keep the canonical row
- keep the field as null where appropriate
- set layer-presence flags correctly
- never silently fill optional context with invented defaults that look like real observations

### 9. Scenario rule

Alignment policy must respect research-object type.

Examples:
- crypto rows outside stock-market hours should not try to force ETF/options context matches
- ETF rows should not depend on ETF-self-context recursion
- stock rows may use richer same-session context when available

### 10. First implementation discipline

Before rebuilding code, the implementation should explicitly define for each first-pass field:
- source artifact class
- join mode (`exact`, `asof`, `window_aggregate`, `monthly_context_attach`)
- tolerance window
- aggregation rule if many-to-one
- missingness behavior

## Scenario-specific dependency rules

### Stock
Stocks may use:
- base market layer
- direct enrichment layer
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

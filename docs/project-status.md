# Project Status

_Last updated: 2026-04-01_

## Goal

Build a historical-data / research / backtest system for crypto strategy modeling that:
- uses long-span historical market data as the main driver
- constructs reusable research datasets and model-facing artifacts
- evaluates strategy families offline before any live promotion decision
- remains auditable through persisted artifacts, tests, and current docs under `docs/`

## Repository direction

This repository has been renamed in intent to **`trading-model`**.

It should retain:
- historical data ingestion for research
- dataset construction
- market-state / regime modeling
- parameter utility modeling
- offline evaluation
- backtests and research reports

Realtime trading / execution responsibilities are being moved to:
- `quantitative-trading`
- <https://github.com/gilmore307/quantitative-trading>

## Current state

The repo is currently in a **split-transition phase**:

1. historical-first strategy-family research remains the primary purpose
2. historical data ingestion is being isolated as its own clean layer
3. some live/runtime/execution code still exists here, but it is no longer the intended long-term home
4. docs are being rewritten to reflect the repo split rather than the earlier hybrid model

## What is already real

### Historical / research foundation
- `src/research/` is substantial
- historical data ingestion is being standardized around monthly partitions
- market-state / regime / parameter-utility dataset builders exist
- snapshot-based and backtest-oriented offline research exists
- research outputs already cover regime quality, separability, ranking, parameter-search previews, and report artifacts

### Documentation / structure
- project Markdown lives under `docs/`
- repo split direction is now explicit
- data-ingestion isolation is now a first-class concern

## Current boundaries

### Keep in this repo
- historical data ingestion
- market-state datasets
- regime discovery / offline labels
- strategy-family research
- parameter utility modeling
- backtests / replay-oriented research
- offline evaluation / reporting

### Move out of this repo
- live runtime workflows
- realtime execution / submit / reconcile / recovery
- live state persistence
- live daemon / alert / notification surfaces
- account/exchange operational execution glue for running strategies live

## Most important next steps

1. finish isolating the historical data ingestion layer
2. finish classifying modules into keep / move / split according to the repo split plan
3. move realtime/execution code into `quantitative-trading`
4. keep `trading-model` cleanly focused on historical modeling / research / backtests

## Validation snapshot

Use targeted validation after each migration chunk.
For Python syntax validation during ongoing refactors:
- `python -m py_compile ...`

## Canonical working TODO

Use `docs/TODO.md` as the current task list.

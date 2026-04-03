# 03 Inputs and Data Contracts

This document defines the required input boundary for `trading-model`.

## Non-negotiable rule

All canonical inputs for this repository must come from upstream repositories:
- `trading-data`
- `trading-strategy`

If data is not supplied through those upstream contracts, it should not become a hidden canonical dependency of this repository.

## Input class A — market/context data from `trading-data`

Examples:
- market bars / candles
- quote/trade aggregates where available
- market-context enrichments
- other upstream-normalized market-state inputs

`trading-model` consumes these as the raw descriptive side of the market-state model.

## Input class B — strategy outputs from `trading-strategy`

Examples:
- family outputs
- variant outputs
- return series
- equity series
- trade outputs
- parameter-region utility surfaces
- ranking or evaluation summaries

`trading-model` consumes these as the explanatory/evaluation side of the model.

## Why both upstreams are required

The unsupervised model should not be built from only one side.

- `trading-data` tells us what the market looked like
- `trading-strategy` tells us how strategies behaved under those conditions

The model is useful only if it can connect the two.

## Required alignment layer

This repo must build a modeling-ready learning table that joins:
- market/context state from `trading-data`
- strategy behavior from `trading-strategy`

That aligned table is the true modeling foundation for this repository.

## Contract design rule

Every important model input should be documented in terms of:
- upstream source repo
- upstream artifact class
- alignment key
- temporal granularity
- whether it is required or optional

## Anti-patterns

Do not let this repo quietly reintroduce:
- local one-off fetch scripts as canonical inputs
- direct raw acquisition ownership
- strategy replay ownership
- state definitions that depend on undocumented side data

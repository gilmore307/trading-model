# 01 Overview

`trading-model` is the repository for building and improving the **unsupervised market-state recognition model**.

Its job is to consume upstream datasets and strategy outputs, learn recurring market-state structure, and produce model outputs that help explain which strategy behavior is suitable under which market conditions.

## Hard role boundary

### `trading-data`
Owns:
- market-data acquisition
- context-data acquisition
- normalization and upstream handoff datasets

### `trading-strategy`
Owns:
- strategy execution over historical data
- variant/family output generation
- strategy result surfaces and evaluation artifacts

### `trading-model`
Owns:
- consuming upstream data from the two repositories above
- building layered market-state learning tables
- training / refreshing unsupervised market-state models
- evaluating whether discovered states are useful for strategy selection
- improving the model as new data arrives

## Core design principle: layered dependency, not brittle dependency

The model must be designed so that data dependencies are layered.
That means:
- the model should keep working when some optional context layers are missing
- not every research object depends on the exact same upstream context stack
- optional context should enrich the model, not become a hidden single point of failure

In other words, the repository should support **graceful degradation**.
If a higher layer is missing, the model should still run on the lower layers that remain available.

## Three research-object scenarios

### 1. Stock research objects
For stock research/trading candidates, upstream data may include:
- full Alpaca stock market data for the researched symbol
- stock news and options context
- ETF holdings base snapshots
- per-symbol ETF context records under `context/constituent_etf_deltas/<SYMBOL>.md`

Stocks therefore may use the richest context stack.

### 2. ETF research objects
For ETF research/trading candidates:
- the ETF itself may use its own Alpaca market/news/options data
- ETF -> ETF context layering should not be treated as the primary self-context path
- non-ETF macro/cross-asset context may still be used where relevant

So ETF research objects should primarily rely on their own direct market/context data, not an ETF-self-context recursion.

### 3. Crypto research objects
Crypto trades 24 hours.
That means:
- during stock-market trading hours, crypto research may also use corresponding ETF and ETF-options context where relevant
- outside stock-market trading hours, crypto research should rely on its own base market data path rather than stock/ETF market context

So crypto context is time-conditional and must not become dependent on stock-market layers being always present.

## Modeling consequence

This repository should model inputs in layers such as:
- base market layer
- optional derivatives/context layer
- optional cross-asset / ETF-context layer
- strategy-behavior evaluation layer

The model must still be runnable when only the base layer and strategy-output layer are present.

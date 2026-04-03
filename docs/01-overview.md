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
- building market-state datasets for modeling
- training / refreshing unsupervised market-state models
- evaluating whether discovered states are useful for strategy selection
- improving the model as new data arrives

## What this repo must not do

This repo must not drift back into:
- raw market-data fetching
- exchange/source adapters
- strategy execution ownership
- live trading runtime ownership
- mixed hybrid responsibilities from the old repo shape

## Core modeling goal

The model should answer questions like:
- what recurring market-state structures appear in the upstream data?
- how should those states be represented without hand-labeling them first?
- do those discovered states meaningfully separate strategy behavior and parameter utility?
- as new data arrives, how should the state model be refreshed or improved?

## Core modeling stance

The current modeling stance is:
- **unsupervised first**
- market states are discovered from data, not predefined by fixed labels
- strategy outputs are used to evaluate whether discovered states are useful, not to directly define the state classes up front

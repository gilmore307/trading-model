# 01 Overview

`trading-model` is the repository for building and improving the **unsupervised market-state recognition model**.

Its job is to:
- discover recurring market states from market data itself
- test whether those discovered states are useful for strategy selection
- build a clean bridge from state recognition to policy selection without contaminating state definition with strategy outcomes

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
- consuming upstream market data from `trading-data`
- discovering recurring market states from market behavior
- consuming strategy outputs from `trading-strategy` only after state discovery
- evaluating whether discovered states are useful for strategy selection
- improving the state model as new data arrives

## Core separation principle

This repository must keep two different questions separate.

### Question 1 — state discovery
Using only market data:
- what does the market currently look like?
- do these market shapes recur?
- do they form stable unsupervised clusters?

### Question 2 — strategy-state mapping
After states are discovered:
- which strategies perform better in which states?
- which parameter regions are favored in which states?
- where is the oracle gap especially large?

The second question must be built on top of the first.
It must not leak backward into the state-definition step.

## Why this separation matters

If strategy outcomes are allowed to influence clustering directly, then the state definition becomes contaminated by the result.
That creates two problems:
- it becomes unclear whether the model discovered a real market state or merely a strategy-success partition
- later claims that the state can guide strategy selection become less convincing because the state was already shaped by strategy outcomes

So the clean pipeline is:
- market data -> state clusters -> attach strategy/oracle outcomes -> estimate conditional utility -> use state for policy selection

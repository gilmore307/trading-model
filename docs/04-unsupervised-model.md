# 04 Unsupervised Model

This document defines the intended model structure.

## Model objective

The objective is to learn recurring market-state structure from market data itself, without requiring hand-labeled classes and without allowing strategy outcomes to contaminate state definition.

## Core rule

The model must be built in two stages.

### Stage 1 — State discovery
Use only market-side information to define states.

### Stage 2 — Strategy-state mapping
After states are fixed, attach strategy/oracle outcomes to evaluate whether the states are useful.

## First base-only model spec

This is the minimum viable model path.

### Purpose

The base-only model should answer:
- can the repository discover recurring unsupervised market states using only market behavior?
- are those discovered states stable enough to be meaningful?

### Required inputs for state discovery
From `trading-data` only:
- OHLCV or equivalent direct market rows
- enough continuous history to compute past-window market features

### Canonical feature family for base-only v1
The first base-only state-discovery model should start with compact features derived only from market behavior:
- short-horizon returns
- medium-horizon returns
- short realized volatility
- medium realized volatility
- short range width
- medium range width
- volume burst / relative activity
- simple trend slope / directionality from price only

The key design rule is:
- no strategy returns
- no oracle labels
- no variant success statistics
- no downstream policy information

## Output of stage 1
The first discovery stage should produce:
- a state vector per canonical timestamp
- an unsupervised cluster/state assignment
- a state summary for each discovered cluster
- stability diagnostics for the discovered states

## Stage 2: strategy-state mapping
Once states are fixed, the repository should attach:
- strategy outputs
- oracle outputs
- variant / family identifiers

Then it should answer:
- which variant performs best within each state?
- which parameter region is favored within each state?
- where is the oracle gap especially large?

## Model composite construction principle

The model composite should be built only after the state clusters already exist.

The logic is:
- discover market states from market data alone
- evaluate which variants perform best conditional on each discovered state
- map each state to a preferred variant or policy
- use that mapping to build the model composite

## Primary evaluation principle

The main way to judge model quality is:
- compare the **model composite** against the **oracle composite**

If grouping were perfect, then in theory:
- the model composite could equal the oracle composite

So the main quality question is:
- how much of the oracle composite does the model composite capture?

## Why this is the cleanest design

This design avoids a common failure mode:
- defining states using information that already contains the strategy result

By keeping discovery and evaluation separate, the repository can make a much stronger claim:
- the states are real recurring market structures first
- only afterward do we test whether they are useful for policy selection

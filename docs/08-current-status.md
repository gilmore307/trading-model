# 08 Current Status

## Current state

The repository has been intentionally stripped down so the old hybrid implementation does not keep leaking outdated assumptions into the new design.

At this stage, the docs are the source of truth.

## Current design commitment

This repository will be rebuilt around one clear line:
- consume upstream data from `trading-data`
- consume upstream strategy outputs from `trading-strategy`
- build an unsupervised market-state model
- support layered dependency rather than brittle dependency
- continuously improve that model as new upstream data arrives

## Current policy commitment

The repository now treats stock, ETF, and crypto as different research-object classes with different valid layer policies.
That policy distinction is part of the design, not an implementation afterthought.

## Current evaluation commitment

The primary evaluation logic is now explicit:
- build a model composite from the discovered states
- compare the model composite against the oracle composite
- treat the oracle gap as the main model-quality signal

If grouping were perfect, the model composite could in theory equal the oracle composite.
That is the north-star interpretation for the repository.

## What comes next

Next design work should make the base-only path more concrete by defining:
- exact per-field aggregation rules
- the first compact base-only feature set
- the first clustering choice
- the first composite-evaluation report shape

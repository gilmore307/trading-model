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

## Current modeling commitment

The first actual model path should be:
- base-market-layer only on the descriptive side
- plus strategy outputs on the evaluation side

In other words, the first real model must be a **base-only model** before optional context layers are added.

## What comes next

Next design work should make the base-only path more concrete by defining:
- exact per-field aggregation rules
- the first compact base-only feature set
- the first clustering choice
- the first usefulness-evaluation report shape

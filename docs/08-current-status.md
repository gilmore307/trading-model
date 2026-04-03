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

## What comes next

Next design work should make the layer policy operational by defining:
- exact field mapping by layer
- exact join rules
- the first base-only model path
- the first comparison workflow for richer layer stacks versus minimal layer stacks

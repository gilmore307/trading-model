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

## Current modeling rule

The model must be able to run under partial upstream availability:
- required base layer
- optional enrichment layers
- optional cross-object context layers

In other words, the model should degrade gracefully rather than fail just because one context layer is absent.

## What comes next

Next implementation work should follow the docs rather than trying to revive old code paths.
The next important design step is to finalize the layer policy and field-level mapping for the first aligned learning table.

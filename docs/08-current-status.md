# 08 Current Status

## Current state

The repository has been intentionally stripped down so the old hybrid implementation does not keep leaking outdated assumptions into the new design.

At this stage, the docs are the source of truth.

## Current design commitment

This repository will be rebuilt around one clear line:
- consume upstream data from `trading-data`
- consume upstream strategy outputs from `trading-strategy`
- build an unsupervised market-state model
- continuously improve that model as new upstream data arrives

## What comes next

Next implementation work should follow the docs rather than trying to revive old code paths.

# 08 Current Status

## Current state

The repository has been intentionally stripped down so the old hybrid implementation does not keep leaking outdated assumptions into the new design.

At this stage, the docs are the source of truth.

## Current design commitment

This repository will be rebuilt around one clear line:
- use `trading-data` to discover market states
- use `trading-strategy` only after state discovery to evaluate and map policies
- build an unsupervised market-state model first
- build strategy-state mapping second

## Current evaluation commitment

The primary evaluation logic is now explicit:
- first discover states from market data alone
- then build a long-format state-evaluation table
- then estimate state -> preferred-variant mappings
- then build a model composite from those mappings
- compare the model composite against the oracle composite
- treat the oracle gap as the main model-quality signal

## Current stage-2 commitment

The v1 defaults are now explicitly defined for:
- state-winner score
- state-winner tie-break cascade
- posterior-gated stitching with hysteresis and dwell rules
- four-layer oracle-gap reporting

## What comes next

The next remaining design work is mostly threshold calibration and implementation detail, not basic conceptual structure.

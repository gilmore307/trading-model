# 06 Output Boundary

This document defines what `trading-model` should publish.

## Core output types

This repository should publish outputs such as:
- market-only state tables
- state-evaluation tables with strategy/oracle outcomes attached after discovery
- unsupervised state-model artifacts
- cluster/state labels
- state -> preferred-variant mappings
- model composite outputs
- oracle-comparison reports
- comparisons across layer policies
- conclusions about which states and which layer stacks appear useful or not useful

## Primary evaluation output

The most important output is the comparison between:
- model composite
- oracle composite

This comparison is the main scorecard for the repository.

## Boundary reminder

Outputs from `trading-model` are model-side research outputs.
They are not live execution actions.

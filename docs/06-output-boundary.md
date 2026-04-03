# 06 Output Boundary

This document defines what `trading-model` should publish.

## Core output types

This repository should publish outputs such as:
- aligned modeling datasets
- layer-availability-aware learning tables
- unsupervised state-model artifacts
- cluster/state labels
- state summaries and explanations
- strategy-separation analysis
- comparisons across layer policies
- conclusions about which states and which layer stacks appear useful or not useful

## What it should not publish

This repository should not turn back into:
- a market-data source repo
- a strategy execution repo
- a live runtime repo

## Boundary reminder

Outputs from `trading-model` are model-side research outputs.
They are not live execution actions.

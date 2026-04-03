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

## Output sizing rule

Outputs and reports must not be allowed to grow into oversized monolithic files.

Default rule:
- partition outputs early
- prefer many bounded files over one ever-growing file
- keep partitioning aligned with how the research will actually be queried and refreshed

## Required partition axes

By default, generated outputs should be partitioned by:
- `symbol`
- `family`
- `variant`
- `month`

Depending on the artifact type, not every axis must appear in every file path, but these are the canonical partition dimensions the repo should use.

## Practical partition policy

### State tables
Partition by at least:
- `symbol`
- `month`

### State-evaluation tables
Partition by at least:
- `symbol`
- `family`
- `variant`
- `month`

### Model composite outputs
Partition by at least:
- `symbol`
- `month`

### Oracle-comparison reports
Partition by at least:
- `symbol`
- `family` when family-scoped
- `month`

### State -> preferred-variant mapping outputs
Partition by at least:
- `symbol`
- model/version scope
- optionally `month` or training-window id when mappings are refreshed periodically

## Why this rule matters

This keeps the repo operationally healthy by preventing:
- oversized single-file artifacts
- slow read/write/update cycles
- awkward partial refreshes
- output formats that become hard to inspect or diff

It also matches the upstream partition logic already used in related repositories.

## Primary evaluation output

The most important output is the comparison between:
- model composite
- oracle composite

But even this comparison should be emitted in partitioned form rather than as one giant file.

## Boundary reminder

Outputs from `trading-model` are model-side research outputs.
They are not live execution actions.

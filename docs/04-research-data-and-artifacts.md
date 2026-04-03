# 04 Research Data and Artifacts

This document defines the storage and artifact boundary for `trading-model`.

## Core rule

This repository should remain centered on research-side artifacts.
It should store and publish artifacts that support offline analysis, model development, and promotion decisions.

## Artifact families

### Research datasets
Research datasets are the durable inputs and derived tables used for:
- feature engineering
- market-state modeling
- strategy comparison
- selector/model learning

These are the most important durable artifact family for this repository.

### Reports
Reports are exported, human-readable summaries of research results.
They may include:
- backtest summaries
- family comparison outputs
- ranking tables
- model evaluation summaries
- promotion recommendation reports

### Logs
Logs are execution traces from research jobs and maintenance/pipeline runs.
They help with debugging and auditing, but they are not the canonical research result.

## Boundary between artifact families

Use this distinction:
- research datasets = model/research inputs and durable data products
- reports = readable exported conclusions and summaries
- logs = traces of how jobs ran

## Current repository direction

This repo should not define itself around live runtime state.
Its artifact center of gravity should be:
- research-ready datasets
- comparison outputs
- candidate/model artifacts
- documentation explaining those outputs

## Data ownership note

Historically this repo carried a local `data/` tree, but the current direction is to reduce mixed data ownership and keep the repository focused on documentation, code, and research contracts.
Where large or externalized data storage is used, the docs should describe the contract rather than assume local in-repo data is the canonical source.

## What should be documented clearly

For each important research artifact class, the docs should eventually make clear:
- where it comes from
- what it represents
- whether it is raw, derived, or summarized
- which upstreams it depends on
- which downstream decision it supports

## Practical rule for future cleanup

When deciding whether an artifact belongs in the main documentation path, ask:
- is it part of the current research workflow?
- is it durable and still relevant?
- does it help explain how the repo is supposed to work now?

If not, it likely belongs in `docs/archive/` rather than the primary numbered path.

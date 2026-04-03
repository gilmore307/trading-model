# 02 Workflow

This document defines the canonical working flow of `trading-model`.

`trading-model` is an upstream historical research and modeling repository.
Its job is to turn upstream inputs into research-ready datasets, feature/state layers, strategy comparisons, selector/model outputs, and promotion-ready candidate outputs.

## End-to-end flow

1. receive upstream inputs
2. validate and normalize research-side inputs
3. build research datasets and artifacts
4. build market-state and feature layers
5. evaluate strategy families and variant surfaces
6. build selector/model layers over strategy outputs
7. compare against Oracle ceilings and strong baselines
8. publish promotion-ready outputs for downstream consumption

## Step 1 — Receive upstream inputs

Primary upstream dependencies:
- `trading-data`
- `trading-strategy`

Expected input classes:
- market/context data handoffs from `trading-data`
- strategy-run outputs from `trading-strategy`

`trading-model` consumes these inputs.
It does not own the primary acquisition workflow or the strategy execution engine as long-term responsibilities.

## Step 2 — Validate and normalize research-side inputs

Before modeling work begins, upstream inputs should be checked for:
- expected path/layout
- schema consistency
- time coverage
- symbol/instrument identity
- readiness for research joins

The goal here is not to rebuild upstream systems.
The goal is to make upstream data usable and trustworthy for research.

## Step 3 — Build research datasets and artifacts

Research-side data preparation should produce:
- reusable research tables
- aligned input datasets for feature/state/model work
- manifests or summaries that make the datasets auditable

This repository should preserve the distinction between:
- durable research datasets
- temporary logs
- exported reports

## Step 4 — Build market-state and feature layers

This repo owns the offline feature and market-state layer, including:
- market-state description
- feature engineering
- regime/state research
- dataset specifications needed by downstream model evaluation

This layer should explain market conditions in a form that can later support:
- family comparison
- state-conditioned ranking
- selector/model learning

## Step 5 — Evaluate strategy families and variant surfaces

This repo should study the strategy-result surface rather than treating single fixed strategies as the only unit of interest.

Main questions:
- which families are worth keeping?
- which variants are robust?
- which regions are dominated or redundant?
- where is there meaningful switching value?

The working unit is usually:
- family
- variant
- parameter region
- state-conditioned behavior

## Step 6 — Build selector/model layers

Above the strategy-result surface, `trading-model` should build:
- selector logic
- regime-aware choice layers
- model outputs that map market state to preferred strategy behavior

This is where the repo moves from “strategy research” into “model research”.
The purpose is to learn which strategy behavior should be preferred under which conditions.

## Step 7 — Compare against Oracle ceilings and strong baselines

Research outputs should preserve multiple comparison anchors:
- strong single-variant baselines
- Oracle ceilings / hindsight upper bounds
- executable model/selector outputs

This comparison is necessary to answer:
- whether switching value really exists
- whether the model captures enough of that value
- whether a candidate is worth promoting downstream

## Step 8 — Publish promotion-ready outputs

The final output of this repository is not live execution.
The final output is a set of promotion-ready research results, for example:
- recommended candidate families/variants
- selector/model outputs
- parameter recommendations
- research reports and supporting artifacts

These outputs may later be promoted into downstream runtime systems.

## Boundary reminder

`trading-model` should own:
- offline research
- feature/state/model development
- strategy comparison
- selector/model evaluation
- promotion-candidate generation

`trading-model` should not reclaim ownership of:
- upstream market-data acquisition
- source-adapter maintenance
- long-running live daemon workflows
- live execution and reconciliation

## Practical reading order

For the current repo docs, read next:
1. `03-inputs-and-data-contracts.md`
2. `04-research-data-and-artifacts.md`
3. `05-market-state-and-features.md`
4. `06-strategy-research.md`
5. `07-promotion-and-output-boundary.md`

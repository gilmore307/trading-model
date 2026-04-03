# 07 Promotion and Output Boundary

This document defines what `trading-model` should output, and where its responsibility ends.

## Core relationship

- `trading-model` is upstream research/modeling
- downstream runtime systems are consumers of promoted outputs

The main downstream runtime is currently `quantitative-trading`.

## What `trading-model` should produce

This repository should produce research outputs such as:
- candidate family/variant recommendations
- selector/model outputs
- ranking and comparison artifacts
- parameter recommendations
- supporting research reports

These outputs may later be promoted into downstream execution systems.

## What promotion means here

Promotion does **not** mean that this repo runs live trading.
Promotion means that research conclusions are converted into explicit downstream-consumable outputs.

Examples:
- a preferred family/variant
- a chosen selector/model definition
- a parameter set worth activating downstream
- a documented recommendation with supporting evidence

## What stays upstream

`trading-model` should keep ownership of:
- historical evaluation
- market-state-aware analysis
- selector/model comparison
- Oracle-gap analysis
- deciding what appears promotion-worthy

## What stays downstream

Downstream runtime systems should keep ownership of:
- live daemon lifecycle
- realtime execution
- reconciliation and recovery
- exchange/account operational behavior
- active runtime health and live execution review

## Important rule

This repo should define and publish the research result.
It should not reclaim operational ownership of the live loop.

## Documentation rule

If an old document is mainly about runtime execution, operational review, or live state management, it should not remain in the primary active reading path for this repository.
Those materials belong either:
- downstream in runtime repos, or
- in `docs/archive/` as historical migration context

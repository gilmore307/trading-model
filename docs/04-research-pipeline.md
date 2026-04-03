# 04 Research Pipeline

This document is the top-level entry for the historical research / backtest pipeline in `trading-model`.

## Purpose

The research pipeline exists to:
- consume and validate upstream handoff artifacts from `trading-data`
- consume and validate upstream strategy outputs from `trading-strategy`
- build derived research inputs
- build model-facing selector/evaluation datasets
- evaluate candidates
- produce promotion-ready research outputs

## Repo role

This pipeline belongs in `trading-model` because it is upstream research work.
It should not depend on the downstream live daemon to function.
It also should not own primary source refresh/adaptation logic that now belongs in `trading-data`.

## Main code areas

Likely touchpoints include:
- `src/pipeline/`
- `src/research/`
- `src/strategies/`
- `src/features/`
- `src/regimes/`
- `scripts/research/`
- `scripts/pipeline/`

Transitional note:
- any remaining `scripts/data/` usage in this repo should be treated as migration residue unless it is specifically about research-side data preparation rather than upstream acquisition

## Expected outputs

Examples:
- backtest result sets
- family/variant evaluation outputs
- candidate-ranking artifacts
- model/parameter recommendation artifacts
- research reports under `reports/`

## Migration direction

Over time, script entrypoints should become cleaner wrappers around organized `src/` modules, while preserving useful operator workflows.

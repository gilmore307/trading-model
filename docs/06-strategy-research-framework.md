# 06 Strategy Research Framework

This document summarizes the strategy-family research role of `trading-model`.

## Purpose

`trading-model` should remain the place where strategy research asks questions like:
- given `trading-strategy` outputs, which families are worth exploring further?
- which variants are robust across historical windows?
- which market-state-aware selectors can approach Oracle?
- which candidates are worth promoting downstream?

## Main code areas

- `src/strategies/`
- `src/research/`
- `src/pipeline/`
- `src/review/` for offline/reporting support

## Related docs

Detailed material already exists in:
- `strategy-research-framework.md`
- `strategy-candidate-pool.md`
- `strategy-family-implementation-plan.md`

This numbered doc is the new high-level entrypoint above those topic docs.

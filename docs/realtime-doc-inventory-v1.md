# Realtime Doc Inventory v1

This document inventories Markdown files that still contain realtime trading / live runtime / execution-system content.

## Status update

A first realtime-doc seed set has now been created in:
- `projects/quantitative-trading/docs/`

That new docs tree is the target home for complete realtime trading documentation.

## A. Core realtime / execution docs

These are primarily about live trading, runtime workflows, execution, reconciliation, or operational review.
They should now be treated as belonging conceptually to `quantitative-trading`.

- `docs/runtime-and-modes.md`
- `docs/execution-artifacts.md`
- `docs/review-operations.md`
- `docs/review-architecture.md`
- `docs/environment-and-operations.md`
- `docs/multi-account-parallel-execution.md`
- `docs/router-composite.md`
- `docs/regime-and-decision-flow.md`
- `docs/state-and-artifacts.md`
- `docs/checkpoints/2026-03-19-execution-ledger-hardening.md`

## B. Hybrid docs: research-oriented, but still containing live/runtime coupling

These need rewriting or splitting.
Parts may stay in `trading-model`, but live/runtime sections should likely move or be removed.

- `docs/parameter-promotion-workflow.md`
- `docs/research-runtime-separation.md`
- `docs/review-automation.md`
- `docs/known-gaps-and-boundaries.md`
- `docs/project-status.md`
- `docs/project-map.md`
- `docs/PIPELINE_AND_ARTIFACT_OVERVIEW.md`
- `docs/components/features.md`
- `docs/market-state-architecture.md`

## C. Repo-split docs that intentionally mention realtime because they define the migration

These should stay in `trading-model` for now because they describe the split itself.

- `docs/repo-split-plan.md`
- `docs/repo-split-classification-v1.md`
- `docs/project-status.md`
- `docs/project-map.md`
- `docs/TODO.md`

## Immediate follow-up use

When tracing code/script migration from docs, start in this order:

1. core realtime docs now seeded under `quantitative-trading/docs/`
2. hybrid docs in `trading-model/docs/` that still need splitting
3. map referenced modules / runners / scripts from those docs into a code inventory

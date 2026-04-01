# Realtime Doc Inventory v1

This document inventories Markdown files that still contain realtime trading / live runtime / execution-system content.

Use this file as the first step before classifying code and scripts.

## A. Core realtime / execution docs

These are primarily about live trading, runtime workflows, execution, reconciliation, or operational review.
They are strong candidates to move with the realtime system into `quantitative-trading`.

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

## D. Historical / research docs with only minor incidental realtime mentions

These can usually stay in `trading-model` and only need light cleanup later.

- `docs/strategy-research-framework.md`
- `docs/strategy-family-implementation-plan.md`
- `docs/strategy-candidate-pool.md`
- `docs/market-state-dataset-spec.md`
- `docs/market-state-description-framework.md`
- `docs/market-state-feature-inventory-v1.md`
- `docs/data-layering-and-git-policy.md`
- `docs/data-sparse-checkout-policy.md`
- `docs/TIME_SERIES_PARTITION_POLICY.md`
- `docs/data-ingestion-architecture.md`

## Immediate follow-up use

When tracing code/script migration from docs, start in this order:

1. Core realtime / execution docs (section A)
2. Hybrid docs with live/runtime coupling (section B)
3. Map referenced modules / runners / scripts from those docs into a code inventory

This keeps the migration grounded in documented responsibilities rather than filename intuition.

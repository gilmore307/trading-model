# crypto-trading docs

This directory is now the **single canonical home for all project Markdown**.

Rules:
- project docs live under `docs/`
- project-local session handoff files do **not** live in the repo root
- session/topic memory belongs in the workspace memory system, not inside this project tree
- generated runtime/research artifacts may be JSON/JSONL under `logs/` and `reports/`, but Markdown docs stay under `docs/`

## Reading order

1. `project-status.md` — current project state and current phase
2. `TODO.md` — canonical current task list
3. `strategy-research-framework.md` — current research operating model
4. `market-state-description-framework.md` — market-state description priority
5. `strategy-candidate-pool.md` — open-ended candidate family pool
6. `project-map.md` — code/module orientation
7. `known-gaps-and-boundaries.md` — current limits and non-goals
8. topic docs as needed

## Core docs

- `project-status.md`
- `TODO.md`
- `project-map.md`
- `strategy-research-framework.md`
- `strategy-candidate-pool.md`
- `runtime-and-modes.md`
- `environment-and-operations.md`
- `state-and-artifacts.md`
- `execution-artifacts.md`
- `regime-and-decision-flow.md`
- `review-architecture.md`
- `review-operations.md`
- `review-automation.md`
- `research-runtime-separation.md`
- `parameter-promotion-workflow.md`
- `multi-account-parallel-execution.md`
- `known-gaps-and-boundaries.md`
- `documentation-policy.md`
- `TIME_SERIES_PARTITION_POLICY.md`
- `FAMILY_VARIANT_ARTIFACT_POLICY.md`
- `PIPELINE_AND_ARTIFACT_OVERVIEW.md`

## Supporting docs

- `components/features.md`
- `components/market.md`
- `checkpoints/2026-03-19-execution-ledger-hardening.md`

## Repo layout summary

- `src/` — application code
- `tests/` — tests
- `scripts/` — CLI/script entrypoints (`data/`, `review/`, `runtime/`, `research/`)
- `logs/` — runtime/research artifacts
- `reports/` — exported review outputs
- `docs/` — all project Markdown

## Cleanup note

As of 2026-03-20, legacy root-level handoff Markdown, retired closeout remnants, and old backup clutter were removed from the repo so the project state is documented in one place instead of being scattered across the root.

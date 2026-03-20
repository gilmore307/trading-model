# crypto-trading docs

This directory is now the **single canonical home for all project Markdown**.

Rules:
- project docs live under `docs/`
- project-local session handoff files do **not** live in the repo root
- session/topic memory belongs in the workspace memory system, not inside this project tree
- generated runtime/research artifacts may be JSON/JSONL under `logs/` and `reports/`, but Markdown docs stay under `docs/`

## Reading order

1. `project-status.md` — current project state and what changed recently
2. `project-map.md` — code/module orientation
3. `multi-account-parallel-execution.md` — current execution model direction
4. `research-runtime-separation.md` — offline research vs live runtime boundary
5. `parameter-promotion-workflow.md` — historical tuning -> live activation workflow
6. `known-gaps-and-boundaries.md` — current limits and non-goals
7. topic docs as needed

## Core docs

- `project-status.md`
- `project-map.md`
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

## Supporting docs

- `components/features.md`
- `components/market.md`
- `checkpoints/2026-03-19-execution-ledger-hardening.md`

## Repo layout summary

- `src/` — application code
- `tests/` — tests
- `scripts/` — CLI/script entrypoints
- `logs/` — runtime/research artifacts
- `reports/` — exported review outputs
- `docs/` — all project Markdown

## Cleanup note

As of 2026-03-20, legacy root-level handoff Markdown, retired closeout remnants, and old backup clutter were removed from the repo so the project state is documented in one place instead of being scattered across the root.

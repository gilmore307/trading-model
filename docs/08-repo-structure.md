# 08 Repo Structure

This document defines the active repository structure for `trading-model` after the docs cleanup.

## Top-level areas

- `docs/` — active project documentation
- `docs/archive/` — historical, transitional, or no-longer-primary documents retained for reference
- `src/` — source code for research, modeling, and related support modules
- `scripts/` — entrypoints and operator helpers that still remain useful
- `tests/` — automated tests
- `config/` — project configuration inputs
- `deploy/` — deployment/service helpers retained during transition

## Docs structure

### Active numbered path
The active reading path is now:
1. `01-overview.md`
2. `02-workflow.md`
3. `03-inputs-and-data-contracts.md`
4. `04-research-data-and-artifacts.md`
5. `05-market-state-and-features.md`
6. `06-strategy-research.md`
7. `07-promotion-and-output-boundary.md`
8. `08-repo-structure.md`
9. `09-project-status-and-next-steps.md`

### Archive
`docs/archive/` stores documents that are still worth retaining for historical reasoning, but are no longer part of the main workflow-oriented reading path.

Current archive buckets include:
- `legacy/` — older design/detail notes that were too granular or partially outdated
- `runtime/` — runtime/execution-oriented documents that are no longer central to this repo
- `split/` — repo-split and transition planning material
- `components/` — old component-level notes
- `checkpoints/` — point-in-time migration checkpoints

## Source-code rule

New work in this repo should continue to prefer organized modules under `src/` rather than scattered root scripts or ad-hoc doc sprawl.

## Documentation rule

The primary docs should explain how the repository works **now**.
Detailed historical reasoning can remain in archive, but the active path should stay short, ordered, and workflow-first.

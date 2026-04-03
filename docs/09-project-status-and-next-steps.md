# 09 Project Status and Next Steps

_Last updated: 2026-04-04_

## Current status

`trading-model` is now documented as a research/modeling upstream repository.
The active docs path has been reduced to a workflow-first set of core documents, while older runtime, split-planning, and detailed topic notes were moved under `docs/archive/`.

## What is already true

- the repository role is historical research, feature/model development, and promotion-candidate generation
- the main docs path is now ordered by workflow rather than by incremental note accumulation
- runtime/execution-heavy documents are no longer mixed into the primary reading path
- old split-planning material is preserved, but downgraded to archive context

## Current boundary

Keep this repository focused on:
- upstream input consumption for research
- research datasets and artifact definitions
- market-state and feature work
- strategy-family and selector/model research
- promotion-ready output generation

Do not let the main docs drift back toward:
- source-adapter ownership
- raw acquisition ownership
- live runtime operations
- execution/reconciliation workflow ownership

## Remaining cleanup opportunities

1. tighten individual active docs further once code boundaries are cleaned up more
2. either delete or continue shrinking archived runtime material after downstream repos fully absorb it
3. keep root/project `README.md` and `TODO.md` aligned with the new docs path
4. continue removing references that imply in-repo local data storage is the long-term center of gravity

## Immediate next steps

- keep the active docs path stable and short
- use archive only for historical/reference material
- when updating docs, prefer editing the active numbered path rather than creating new one-off files
- only add a new top-level doc if it represents a durable workflow stage or core boundary

# Router Composite and Ownership Model

This document backfills the meta-work for router-composite, compare snapshot, and ownership attribution.

## Why this exists

The project does not just ask:

- which strategy is selected right now?

It also needs to answer:

- which account currently owns the live composite position?
- does router selection match current ownership?
- when should switching be visible in review artifacts?

That is why router-composite and compare snapshot are separate but linked concepts.

## Core distinction

### Router-selected strategy

This is the strategy/account the router says should currently be active.

Stored as:

- `router_composite.selected_strategy`
- `compare_snapshot.selected_strategy`
- summary highlight `router_selected:<account>`

### Composite position owner

This is the account that actually owns the currently active composite position.

Stored as:

- `router_composite.position_owner`
- `compare_snapshot.composite_owner`
- summary highlight `composite_owner:<account>`

These two values can differ during transitions or staged switching.

## Compare snapshot role

Primary builder:

- `src/review/compare.py`

The compare snapshot records, for each known account:

- whether it has a position
- position status
- side
- size
- whether it was selected by the router
- whether it owns the composite position

It also adds a `flat_compare` row so review can compare active routing against a flat baseline.

## Current snapshot highlights

Current highlight vocabulary includes:

- `router_selected:<account>`
- `composite_owner:<account>`
- `router_selection_differs_from_position_owner`
- `composite_switch:<action>`

These strings are intentionally compact because they are used both in artifacts and later review summaries.

## Why ownership attribution matters

Without ownership attribution, a later review can easily misread the system.

Example failure mode without ownership:

- router now selects `trend`
- but live position still belongs to `meanrev`
- review incorrectly assumes current pnl or exposure belongs to the selected strategy

Ownership attribution prevents that class of confusion.

## How review uses it today

Current review usage includes:

- carrying `compare_snapshot` into report generation
- exposing router composite review sections
- generating router-vs-best-strategy and router-vs-flat summaries
- preserving router/composite highlights in exported report artifacts

## What is implemented vs not yet implemented

### Already implemented

- compare snapshot row generation
- flat baseline row
- router-selected vs owner distinction
- switch-action visibility in highlights
- exported use in review reports

### Not fully implemented yet

- deeper attribution-aware pnl semantics for composite ownership over long windows
- explicit ownership transition journaling beyond current highlights
- richer switch diagnostics in narrative/report sections

## Operational interpretation

When debugging or reviewing a cycle:

- check `selected_strategy` to see what the router wants now
- check `position_owner` to see who actually owns the composite position now
- if they differ, treat the system as being in transition or mismatch analysis mode

That difference is a feature, not automatically a bug.

## Why this matters for portability

This model is useful both inside and outside OpenClaw because it is persisted into the project’s own artifacts.

That means:

- review exports do not need live session memory to understand router state
- later schedulers or offline tooling can still inspect the relationship between selection and ownership

## Related docs

- `docs/execution-artifacts.md`
- `docs/review-architecture.md`
- `docs/runtime-and-modes.md`

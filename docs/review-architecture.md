# Review Architecture

_Last updated: 2026-03-20_

## Purpose

The review system turns runtime execution history into:
- weekly/monthly/quarterly assessments
- operator-readable execution diagnostics
- parameter discussion inputs
- portable JSON/Markdown report artifacts

## High-level pipeline

Current review flow:

1. runtime writes execution artifacts under `logs/runtime/`
2. per-cycle runtime rows are canonicalized in `src/review/ingestion.py`
3. `src/review/aggregator.py` aggregates history into per-account metrics
4. `src/review/performance.py` normalizes known-account rows
5. `src/review/report.py` builds summaries, sections, executive summary, and actions
6. `src/review/export.py` writes JSON + Markdown artifacts
7. review runners in `src/runners/` expose weekly/monthly/quarterly entrypoints

## Runtime artifact reality

There are now two runtime artifact layers:

### Single-cycle account artifacts
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

These still exist and remain useful as per-account rows.

### Parallel-cycle artifacts
- `logs/runtime/latest-parallel-execution-cycle.json`
- `logs/runtime/parallel-execution-cycles.jsonl`

These reflect the newer intended model where all strategy accounts run in the same shared market cycle.

## Module responsibilities

### `src/review/ingestion.py`
- extract canonical review metrics from one execution artifact row
- merge receipt/raw hints, summary metrics, compare/debug data, and account metrics

### `src/review/aggregator.py`
- load JSONL execution history
- derive cross-cycle metrics such as trade counts, fees, funding, pnl/equity snapshots
- provide per-account aggregated metrics for reports

### `src/review/performance.py`
- guarantee a stable row schema across known accounts
- keep known-account expansion deterministic

### `src/review/report.py`
- build operator-facing report structure
- build performance summaries
- build execution-quality summaries
- build parameter/recommendation sections

### `src/review/export.py`
- export structured review reports to JSON and Markdown
- provide path/filename conventions for report artifacts

## Current output model

A review report currently contains combinations of:
- `meta`
- `sections`
- `metrics.performance`
- `metrics.performance_summary`
- `parameter_candidates`
- `executive_summary`
- `recommended_actions`
- `narrative_blocks`
- execution-quality / anomaly summaries

## Important transition note

Older review/report layers still contain router-composite assumptions in places.
Those should now be treated as transitional.

The intended direction is:
- compare all live strategy accounts directly
- review weekly/monthly/quarterly windows using parallel live-account evidence
- reduce dependence on “single routed winner” framing

## Review cadences

### Weekly
- operational calibration
- execution quality checks
- account comparison for the completed week

### Monthly
- multi-week stability review
- strategy/account comparison
- parameter discussion

### Quarterly
- structural review
- regime coverage / pruning discussion
- long-horizon system fitness

## Current strengths

The review stack already has:
- callable runners
- portable file export
- execution-quality reporting
- excluded-trade tracking
- parameter discussion scaffolding

## Current limitations

Still improving:
- full migration to multi-account parallel semantics
- deeper market-regime narrative sections
- canonical realized/unrealized/funding semantics
- less dependence on legacy router-composite framing

## Related docs

- `execution-artifacts.md`
- `multi-account-parallel-execution.md`
- `review-operations.md`
- `review-automation.md`
- `router-composite.md`

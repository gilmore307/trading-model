# Review Architecture

_Last updated: 2026-03-20_

## Purpose

The review system turns runtime execution history into:
- weekly/monthly/quarterly assessments
- operator-readable execution diagnostics
- realized live-performance summaries for the promoted live strategy
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

The review path should now assume a single promoted live strategy running in one real account.

### Single-cycle account artifacts
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

These are the primary review inputs for live operations.

## Module responsibilities

### `src/review/ingestion.py`
- extract canonical review metrics from one execution artifact row
- merge receipt/raw hints, summary metrics, compare/debug data, and account metrics

### `src/review/aggregator.py`
- load JSONL execution history
- derive cross-cycle metrics such as trade counts, fees, funding, pnl/equity snapshots
- provide live-account aggregated metrics for reports

### `src/review/performance.py`
- guarantee a stable row schema for the active live-account review path
- keep exported performance summaries deterministic

### `src/review/report.py`
- build operator-facing report structure
- build performance summaries
- build execution-quality summaries
- build live-operations recommendations and deviation summaries

### `src/review/export.py`
- export structured review reports to JSON and Markdown
- provide path/filename conventions for report artifacts

## Current output model

A review report currently contains combinations of:
- `meta`
- `sections`
- `metrics.performance`
- `metrics.performance_summary`
- `executive_summary`
- `recommended_actions`
- `narrative_blocks`
- execution-quality / anomaly summaries

## Review cadences

### Weekly
- canonical live-operations review cadence
- realized live-pnl / equity summary for the completed week
- theoretical-signal vs actual-execution deviation review
- execution quality checks while trading can continue

### Monthly
- multi-week realized live-performance summary
- execution deviation trend review
- operational stability review

### Quarterly
- structural execution-system review
- long-horizon live-operations stability review
- broker / exchange / runtime integration review

## Current strengths

The review stack already has:
- callable runners
- portable file export
- execution-quality reporting
- excluded-trade tracking
- a usable cadence structure for weekly/monthly/quarterly live reporting

## Current limitations

Still improving:
- full simplification away from multi-account / router-composite legacy framing
- clearer theoretical-signal vs actual-execution reporting
- canonical realized/unrealized/funding semantics
- cleaner separation between live review and historical model optimization

## Related docs

- `execution-artifacts.md`
- `review-operations.md`
- `review-automation.md`

# Review Architecture

This document backfills the meta-work for the review stack itself.

## Purpose

The review system exists to turn runtime execution history into:

- operator-readable weekly/monthly/quarterly assessments
- candidate parameter discussions
- portable report artifacts that do not require OpenClaw-specific internals to render

## High-level pipeline

Current review flow:

1. runtime writes execution artifacts to `logs/runtime/execution-cycles.jsonl`
2. `src/review/ingestion.py` canonicalizes per-row performance hints
3. `src/review/aggregator.py` aggregates history into per-account metrics
4. `src/review/performance.py` normalizes snapshot rows across known accounts
5. `src/review/report.py` builds summaries, sections, executive summary, and actions
6. `src/review/export.py` writes JSON + Markdown artifacts
7. review runners in `src/runners/` expose weekly/monthly/quarterly entrypoints

## Module responsibilities

### `src/review/ingestion.py`

Purpose:

- extract canonical review metrics from one execution artifact row
- merge receipt/raw hints, summary metrics, and compare snapshot metrics

This module is intentionally permissive so runtime artifacts can evolve without repeated review rewrites.

### `src/review/aggregator.py`

Purpose:

- load JSONL execution history
- derive cross-cycle metrics such as trade counts, exposure, fees, funding, pnl/equity snapshots
- provide per-account aggregated metrics for reports

Current behavior includes:

- account trade counting
- composite/router trade counting
- fee accumulation
- funding accumulation
- review-window filtering using artifact timestamps when available
- timestamp-ordered aggregation rather than trusting JSONL append order for latest-metric semantics
- earliest/latest equity boundary inference inside the requested review window
- equity-change inference from window-bounded start/end snapshots
- earliest/latest unrealized-pnl boundary inference inside the requested review window
- inferred realized-pnl fallback from equity-change, funding, and unrealized-boundary movement when explicit realized window snapshots are absent
- window-consistent total-pnl fallback when only compatibility-style pnl snapshots are present
- exposure percentage estimation

### `src/review/performance.py`

Purpose:

- guarantee a stable row schema across all compare accounts
- keep known-account expansion deterministic

This is the normalization layer between aggregated metrics and higher-level reports.

### `src/review/report.py`

Purpose:

- build operator-facing report structure
- build performance leaderboard and comparison summaries
- build parameter candidate suggestions
- build executive summary / recommended actions / narrative blocks

This is the main interpretation layer.

### `src/review/export.py`

Purpose:

- export structured review reports to JSON and Markdown
- provide path/filename conventions for report artifacts

### review runners

Current callable runners:

- `src/runners/weekly_review.py`
- `src/runners/monthly_review.py`
- `src/runners/quarterly_review.py`

These runners make the review stack schedulable without requiring direct internal imports from operator tooling.

## Current output model

A review report currently contains:

- `meta`
- `sections`
- `compare_snapshot`
- `metrics.performance`
- `metrics.performance_summary`
- `parameter_candidates`
- `executive_summary`
- `recommended_actions`
- `narrative_blocks`

## Section model

Current operator-facing sections:

- `market_regime_summary` (still mostly placeholder)
- `account_comparison`
- `router_composite_review`
- `parameter_review`
- `structural_review` (quarterly)

## Review cadences

### Weekly

Intent:

- safe, small operational calibration candidates
- fee drag / frequency / threshold adjustments
- account comparison for the completed week

### Monthly

Intent:

- multi-week stability review
- strategy-internal parameter discussion
- router behavior over a longer interval

### Quarterly

Intent:

- structural review
- taxonomy / risk / framework discussion
- long-horizon system fitness

## Current strengths

The review stack already has:

- callable runners
- portable file export
- basic operator-readable narrative output
- candidate generation logic tied to actual performance signals
- documentation path for scheduling and operations

## Current limitations

These areas are still improving:

- market regime section is not yet deeply populated
- canonical realized/unrealized/funding semantics are not fully final
- review recommendations are still rule-driven, not deeply diagnostic
- report indexing/latest-pointer convenience is not yet added

## Design intent

The review stack is being built so that:

- the trading core remains portable
- OpenClaw can orchestrate it today
- later non-OpenClaw schedulers can call the same review scripts unchanged

That is why the runner/export boundary matters so much.

## Related docs

- `docs/review-operations.md`
- `docs/review-automation.md`
- `docs/execution-artifacts.md`
- `docs/router-composite.md`

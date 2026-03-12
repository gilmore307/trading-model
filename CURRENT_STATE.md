# CURRENT_STATE

_Last updated: 2026-03-12_

This file is the fast-resume spine for future sessions.

Read this before diving into detailed docs or chat history.

## One-paragraph status

The crypto-trading rebuild now has a real execution artifact chain, a review/report pipeline with weekly/monthly/quarterly runners, portable JSON/Markdown report export, latest-pointer/index convenience files, and a growing documentation spine. The system is structurally much stronger than the earlier demo scaffold, but canonical performance semantics (especially realized/unrealized/funding/equity boundaries) are still being hardened and the project is **not** ready for unattended real-money deployment.

## What is already completed

### Runtime / execution side
- layered regime runner exists
- execution pipeline exists
- decision trace exists
- route reconciliation exists
- execution artifacts persist to `logs/runtime/`
- compare snapshot and router ownership fields are persisted

### Review / reporting side
- canonical row ingestion exists
- history aggregation exists
- review-window-aware aggregation now exists when artifact timestamps are present
- normalized account performance snapshot exists
- operator-facing report sections exist
- parameter candidate generation exists
- executive summary / recommended actions / narrative blocks exist
- JSON + Markdown export exists
- weekly/monthly/quarterly review runners exist
- latest cadence pointers and report index exist

### Meta work already backfilled
- project map
- execution artifacts doc
- review architecture doc
- review operations doc
- review automation doc
- router composite / ownership doc
- regime and decision flow doc
- known gaps / boundaries doc

## Current operator-friendly outputs

### Runtime artifacts
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

### Review artifacts
- `reports/trade-review/*.json`
- `reports/trade-review/*.md`
- `reports/trade-review/latest_weekly.json`
- `reports/trade-review/latest_weekly.md`
- `reports/trade-review/latest_monthly.json`
- `reports/trade-review/latest_monthly.md`
- `reports/trade-review/latest_quarterly.json`
- `reports/trade-review/latest_quarterly.md`
- `reports/trade-review/index.json`

## Current boundaries

Treat as real enough today:
- execution artifact persistence boundary
- review runners and exported report artifacts
- operator/debug/report workflow structure

Do **not** over-claim yet:
- final accounting-grade pnl semantics
- unattended live trading readiness
- fully OpenClaw-independent operator workflow
- fully mature report-side regime explanation

## Highest-priority remaining work

### P0 — realism and semantics
- improve canonical realized/unrealized pnl semantics
- improve funding semantics
- improve equity start/end/change semantics over longer windows

### P1 — report depth
- richer regime narrative in reports
- stronger linkage between regime shifts and review findings
- more diagnostic review explanations beyond current heuristic summaries

### P2 — operator convenience / deployment
- optional notifier wrapper after report generation
- exact scheduler wiring examples when automation is enabled
- optional latest-report convenience beyond current pointers if needed

## Recommended reading order for a new session

1. `CURRENT_STATE.md`
2. `README.md`
3. `docs/project-map.md`
4. `docs/known-gaps-and-boundaries.md`
5. `docs/execution-artifacts.md`
6. `docs/review-architecture.md`
7. `docs/regime-and-decision-flow.md`
8. relevant runner/export/report files

## Recommended next implementation direction

If continuing with best payoff now, prefer:

1. canonical performance semantics hardening
2. richer regime/report integration
3. deployment/operator wrappers

## Verification status

- full test suite currently passes
- latest recorded full validation: `127 passed`

# Project Status

_Last updated: 2026-03-12_

## Goal

Maintain a resumable, auditable view of the crypto-trading rebuild so future sessions can recover project state quickly without depending on chat history.

## Current state

The project is now materially beyond the earlier demo scaffold and has several real layers in place:

1. **Runtime / mode system**
2. **Execution / state control**
3. **Execution artifact persistence**
4. **Review/report pipeline**
5. **Review runner / export / indexing layer**
6. **Growing documentation and handoff spine**

## Major milestones already completed

### Runtime and operations
- Reconciliation before each cycle was integrated so local tracked state is checked against exchange state before normal actions.
- Layered regime, routing, execution decision tracing, and runtime-mode-aware gating are all present as real code paths.
- Execution artifacts are persisted under `logs/runtime/` for both latest-cycle inspection and append-only history review.

### Review stack
- `src/review/performance.py` established a normalized per-account performance input layer.
- `src/review/aggregator.py` added history-based aggregation from execution artifacts.
- Review aggregation now respects weekly/monthly/quarterly window boundaries when artifact timestamps are available, instead of treating the entire history file as one undifferentiated interval.
- Equity start/end/change inference is now tied more explicitly to earliest/latest snapshots inside the requested review window.
- Artifact production now persists `summary.account_metrics`, making the runtime-to-review data path explicit.
- The report stack now includes performance summaries, operator-facing sections, parameter candidates, executive summaries, recommended actions, and narrative blocks.
- Weekly, monthly, and quarterly review runners now exist and export JSON + Markdown artifacts.
- Review export now maintains latest-cadence pointers and a rolling `index.json` for operator convenience.

### Meta-work / documentation
- Documentation now covers execution artifacts, review architecture, router-composite ownership, regime/decision flow, automation notes, and explicit known gaps/boundaries.
- A project map and fast-resume `CURRENT_STATE.md` now exist to make future session recovery easier.

### Verification history
- Earlier full validation: `107 passed`
- Intermediate milestones: `115`, `118`, `121`, `124`, `126` passed
- Current full validation: `127 passed`

## Open gaps

1. stronger canonical realized/unrealized/funding semantics
2. stronger equity start/end/change semantics over longer review windows
3. deeper report-side regime explanation and integration
4. optional notifier/deployment wiring beyond current runner/export structure

## Current guidance

Use the system today for:
- architecture validation
- operator review
- artifact-driven debugging
- strategy/account comparison
- workflow hardening toward future production readiness

Do not treat the current state as:
- unattended real-money trading ready
- final accounting-grade review semantics
- fully OpenClaw-independent in operator experience

## Next best step

Continue hardening canonical performance semantics, especially realized/unrealized/funding/equity meaning, while preserving the now-established runner/export/docs spine.

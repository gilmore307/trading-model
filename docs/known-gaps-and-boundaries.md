# Known Gaps and Boundaries

This document backfills the meta-work for realism boundaries and currently known gaps.

## Purpose

The system now has meaningful runtime, review, and reporting structure.

That does **not** mean every metric or automation path should be treated as final truth.

This document makes those boundaries explicit so operators do not over-trust parts of the system that are still transitional.

## Current safe assumptions

These parts are stable enough to treat as real project structure:

- runtime mode model exists and matters
- regime -> route -> execute flow is the intended architecture
- execution artifacts are the persistence boundary between runtime and review
- weekly/monthly/quarterly review runners are real callable entrypoints
- review artifacts are intentionally portable and not tied to OpenClaw internals

## Current transitional areas

### 1. Canonical performance semantics are still improving

Current review fields are useful, but some semantics are still maturing:

- realized pnl
- unrealized pnl
- funding
- equity start/end over longer windows
- drawdown metrics

Meaning:

- they are valid as a development/review interface
- they should not yet be treated as audited production accounting

### 2. Review recommendation logic is still heuristic

Current parameter candidates are generated from rule-based signals such as:

- fee drag
- negative pnl
- high exposure
- router underperformance

Meaning:

- useful for operator review
- not yet sufficient for blind auto-adoption

### 3. Market regime report depth is uneven

The regime pipeline itself is architected, but report-level regime explanation is not yet as rich as the performance/report path.

Meaning:

- regime logic exists
- regime reporting/explanation still has room to catch up

### 4. Portability is a goal, not a fully completed state

The project is being built so the trading/review core can later run outside OpenClaw.

Meaning:

- code entrypoints and report runners are increasingly portable
- orchestration, notification, and operator convenience still benefit from OpenClaw today

## What should not be over-claimed yet

The project should **not** currently be described as:

- unattended real-money trading ready
- fully production-accounting accurate in every review field
- fully independent from OpenClaw in operator workflow
- final in its review semantics

## What is already true enough to rely on

It **is** fair to say that the project already has:

- a real execution artifact chain
- a real review pipeline
- real weekly/monthly/quarterly runners
- real exported report artifacts
- growing documentation/runbook coverage

## Operator rule of thumb

Use the system today for:

- architecture validation
- operator review
- strategy/account comparison
- debugging and auditability
- workflow shaping for later production hardening

Do **not** use the current state as justification for:

- blind live deployment
- automatic parameter mutation without supervision
- claiming final accounting-grade pnl semantics

## Near-term hardening priorities

Most important realism upgrades still to come:

1. stronger canonical realized/unrealized/funding semantics
2. richer regime narrative and explanation in reports
3. report pointer/index conveniences for easier operations
4. clearer scheduler wiring for routine review generation

## Why this document matters

Without an explicit boundaries document, a fast-moving system can look more complete than it really is.

This file exists to prevent that failure mode.

## Related docs

- `docs/review-architecture.md`
- `docs/review-operations.md`
- `docs/review-automation.md`
- `docs/execution-artifacts.md`
- `docs/regime-and-decision-flow.md`

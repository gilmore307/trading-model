# Known Gaps and Boundaries

_Last updated: 2026-03-20_

This document makes the current project limits explicit so the system is not over-trusted while it is still being rebuilt.

## Safe assumptions today

These are real enough to rely on as current structure:
- runtime modes matter, but the active daemon/runtime layer now centers on `develop` / `trade` / `test` / `reset`
- execution submission / verify / reconcile / recovery code exists
- execution artifacts are the persistence boundary between runtime and review
- weekly/monthly/quarterly review runners are real entrypoints
- snapshot-based offline research is real and usable
- multi-account parallel execution research/runtime machinery exists, but the current live-operations interpretation is a single promoted strategy on one real account

## Transitional areas

### 1. Parallel execution rollout is not fully hardened yet
The project has moved away from single-route-only execution and now has a parallel-cycle path, but the full downstream stack is still catching up.

Meaning:
- runtime direction is correct
- some artifact/report/notifier layers still need cleanup

### 2. Execution-environment isolation still needs work
A recent anomaly showed that dry-run-style local state contamination is still possible.

Meaning:
- dry-run / test / live-trade state and artifacts are not isolated strongly enough yet
- this is an execution-integrity risk, not just a cosmetic issue

### 3. Canonical performance semantics are still improving
Current review fields are useful, but some semantics are still maturing:
- realized pnl
- unrealized pnl
- funding
- equity start/end over longer windows
- drawdown metrics

Meaning:
- valid for engineering review and comparative debugging
- not yet audited production accounting

### 4. Review recommendation logic is still heuristic
Current parameter candidates are useful operator hints, not auto-trust outputs.

Meaning:
- useful for supervised tuning
- not safe for blind auto-adoption

### 5. Historical replay is still snapshot-based
The research path is real, but it still starts from historical snapshot JSONL instead of rebuilding from raw market history.

Meaning:
- offline research exists
- the raw historical replay builder is still a major missing piece

## What should not be over-claimed yet

The project should **not** currently be described as:
- unattended real-money trading ready
- fully production-accounting accurate in every review field
- fully hardened against execution-environment contamination
- final in its parallel live execution rollout
- final in its review semantics

## What is already true enough to say

It **is** fair to say the repo already has:
- a real runtime daemon path
- a real execution artifact chain
- a real review pipeline
- a real offline research path
- a partially landed multi-account parallel execution path
- current docs consolidated under `docs/`

## Near-term hardening priorities

1. harden dry-run/test/live isolation
2. finish multi-account parallel rollout in reporting/review layers
3. strengthen canonical realized/unrealized/funding/equity semantics
4. build raw historical replay
5. complete explicit parameter promotion / rollback workflow

## Related docs

- `docs/README.md`
- `project-status.md`
- `multi-account-parallel-execution.md`
- `research-runtime-separation.md`
- `parameter-promotion-workflow.md`
- `review-architecture.md`

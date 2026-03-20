# Multi-Account Parallel Execution

_Last updated: 2026-03-20_

## Goal

Run all strategy accounts in parallel:

- `trend`
- `crowded`
- `meanrev`
- `compression`
- `realtime`

The market-state / regime-detection layer may remain shared, but real execution should no longer be limited to one routed account per cycle.

## Why this changed

The old single-route model was wrong for the intended operating model.
The desired system is:
- all accounts always online
- all accounts independently evaluate the shared market state
- all accounts may act in the same cycle if their own executor conditions are met
- weekly/monthly/quarterly review then compares and stitches market-style periods across all accounts

## Current status

### Already landed
- `src.strategies.executors.build_parallel_plans(output)` exists
- `ExecutionPipeline.build_parallel_plans(output)` exists
- `ExecutionPipeline.run_cycle_parallel()` exists
- daemon has started moving onto the parallel-cycle path
- parallel execution artifacts are now being written

### Current account mapping
- `trend -> trend`
- `range -> meanrev`
- `compression -> compression`
- `crowded -> crowded`
- `shock -> realtime`

### What this means right now
The codebase is no longer conceptually locked to a single real account per cycle.
However, the downstream layers are still catching up.

## Still transitional

1. review/report layers still contain older single-route assumptions in places
2. notifier/output summarization is only partially parallel-aware
3. state contamination guards between dry-run/test/live need hardening
4. per-account artifact consumers still need a cleaner canonical parallel shape

## Immediate hardening priorities

### P1
- tighten state isolation between dry-run/test/live execution paths
- make per-account parallel artifacts the primary review input
- remove remaining single-route assumptions from daemon/reporting glue

### P2
- revise weekly/monthly/quarterly review to compare parallel live accounts directly
- reduce dependence on router-composite assumptions in operator reporting

### P3
- support cleaner per-account execution/recovery summaries and account-level operational dashboards

## Architectural rule

Going forward:
- shared market-state detection is allowed
- shared single-account routing as the only real execution path is not
- every strategy account must be able to trade in the same cycle if its own executor conditions are met

# Multi-Account Parallel Execution

_Last updated: 2026-03-20_

## Goal

Run all strategy accounts in parallel:

- `trend`
- `crowded`
- `meanrev`
- `compression`
- `realtime`

The market-state / regime-detection layer may remain shared, but execution should no longer be limited to a single routed account per cycle.

## Current reality

The current daemon/execution pipeline is still primarily **single-plan / single-account**:

- one `regime_output`
- one routed `plan.account`
- one real execution path per cycle
- other strategy plans exist only as `shadow_plans`

This does **not** match the desired always-on parallel-account model.

## First implemented step

A new parallel-plan layer now exists conceptually and in code:

- `src.strategies.executors.build_parallel_plans(output)`
- `ExecutionPipeline.build_parallel_plans(output)`

This produces one real `ExecutionPlan` per strategy/account pair using fixed always-on account mapping:

- `trend -> trend`
- `range -> meanrev`
- `compression -> compression`
- `crowded -> crowded`
- `shock -> realtime`

At this stage, this is a **planning skeleton**, not yet full parallel real execution.

## Next implementation steps

### P1
- add a multi-result cycle structure
- execute each strategy/account plan independently in the same cycle
- keep per-account verification / reconcile isolated

### P2
- persist per-account execution artifacts in one shared cycle artifact
- update notifier / daemon logging to summarize all accounts

### P3
- revise review layer so weekly/monthly review compares parallel live accounts directly
- reduce dependence on router-composite assumptions in reporting

## Architectural rule

Going forward:

- shared market-state detection is allowed
- shared single-account routing as the only real execution path is not
- every strategy account should be able to trade in the same cycle if its own executor conditions are met

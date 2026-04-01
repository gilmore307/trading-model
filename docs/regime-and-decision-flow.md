# Regime and Decision Flow

This document backfills the meta-work for the regime pipeline and execution decision path.

## Purpose

The system is designed around this rule:

- classify regime first
- route second
- execute third

The intent is to avoid treating execution logic as the place where market understanding happens.

## High-level flow

Current decision chain:

1. market data is ingested into the shared market hub
2. layered regime classification is computed
3. a route decision is derived from the final regime
4. a decision summary is generated
5. execution pipeline applies runtime mode policy and route constraints
6. an execution plan is produced or blocked
7. execution/reconciliation artifacts are persisted for later review

## Main entrypoints

### Regime runner

Primary file:

- `src/runners/regime_runner.py`

Produces:

- `RegimeRunnerOutput`

Important fields:

- `background_4h`
- `primary_15m`
- `override_1m`
- `final_decision`
- `route_decision`
- `decision_summary`

### Execution pipeline

Primary file:

- `src/execution/pipeline.py`

Produces:

- `ExecutionCycleResult`
- `ExecutionDecisionTrace`

## Layered regime model

The regime system is intentionally layered.

### 4h background layer

Purpose:

- provide higher-timeframe structure and context
- influence the broader directional interpretation

Typical role:

- macro trend / context bias
- slower-moving structural signals

### 15m primary layer

Purpose:

- provide the main ordinary regime classification

Typical role:

- decide among trend/range/compression/chaotic when no override dominates

### 1m override layer

Purpose:

- detect fast event-like conditions

Typical role:

- short-horizon shock override
- rapid dislocation/liquidation response

## Regime families

Current regime taxonomy:

- `trend`
- `range`
- `compression`
- `crowded`
- `shock`
- `chaotic`

Current route/account mapping:

- `trend` -> `trend`
- `range` -> `meanrev`
- `compression` -> `compression`
- `crowded` -> `crowded`
- `shock` -> `realtime`
- `chaotic` -> no-trade

## Decision summary semantics

The regime runner produces both:

- a raw route decision
- a summarized decision payload

This summary is what the execution pipeline uses as the first compact explanation layer.

Typical fields include:

- final regime
- confidence
- tradable state
- routed account / strategy family
- trade_enabled
- allow_reason
- block_reason
- diagnostics

## Execution gating order

Within the execution pipeline, the decision does not go straight to order placement.

Current gating sequence is roughly:

1. check runtime mode policy
2. check whether the decision itself is tradable / enabled
3. build an execution plan if allowed
4. check route freeze / route enabled state
5. apply reconciliation / controller policy feedback
6. decide whether execution can proceed or must hold

## Runtime mode interaction

Runtime mode is not just a label. It changes whether normal routing is allowed.

Examples:

- `develop` may block normal routing workflows
- `trade` permits normal routing
- `test` and `reset` are exceptional operational states with different policy implications from normal trading

See also:

- `docs/runtime-and-modes.md`

## ExecutionDecisionTrace role

`ExecutionDecisionTrace` is the compact explanation of why a cycle did or did not progress.

Important fields:

- `mode`
- `mode_allows_routing`
- `decision_trade_enabled`
- `route_trade_enabled`
- `pipeline_trade_enabled` — legacy summary bit kept for compatibility; now means `submission_allowed`
- `pipeline_entered`
- `submission_allowed`
- `submission_attempted`
- `allow_reason`
- `block_reason`
- `diagnostics`

This object matters because it provides a stable operator/debug layer even when the internal pipeline grows more complex.

## Why the flow is split this way

The architecture intentionally separates:

- market interpretation
- routing intent
- execution permission
- reconciliation feedback

That separation makes it easier to:

- debug misbehavior
- explain no-trade cycles
- export compact artifact summaries
- evolve one layer without rewriting every other layer

## Current strengths

This flow already provides:

- layered classification instead of flat one-shot labeling
- explicit route/no-route handling
- explicit decision trace and block reasons
- persistent execution artifacts for later review

## Current limitations

Still improving:

- richer market regime narrative in reports
- clearer long-window attribution between regime transitions and realized pnl
- deeper structural diagnostics when regime confidence is weak or conflicting

## Related docs

- `docs/runtime-and-modes.md`
- `docs/execution-artifacts.md`
- `docs/review-architecture.md`
- `docs/router-composite.md`

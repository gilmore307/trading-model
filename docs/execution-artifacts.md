# Execution Artifacts

This document backfills the meta-work for the execution artifact path.

## Purpose

Execution artifacts are the bridge between:

- runtime execution decisions
- later review/report generation
- operator debugging
- future portability outside OpenClaw orchestration

The goal is to preserve one canonical per-cycle record that can be:

- inspected directly by an operator
- replayed into review aggregation
- extended without repeatedly redesigning downstream review code

## Current artifact files

Runtime artifacts are written under:

- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

## Writer entrypoint

Primary writer:

- `src/runners/execution_cycle.py`

Key functions:

- `build_execution_artifact(result)`
- `persist_execution_artifact(result)`

## Artifact model

Each execution cycle artifact currently contains three important layers.

### 1. Raw execution-cycle payload

The artifact starts from `asdict(result)` on `ExecutionCycleResult`.

This preserves the detailed runtime output from the execution pipeline.

### 2. Compare snapshot

Added under:

- `compare_snapshot`

Produced by:

- `src/review/compare.py`

Purpose:

- preserve account state comparison for the cycle
- preserve router-selected strategy vs actual composite owner
- preserve flat baseline row for later review comparison

### 3. Summary layer

Added under:

- `summary`

This is the operator/review-oriented compact layer.

Current fields include:

- `symbol`
- `runtime_mode`
- `regime`
- `confidence`
- `plan_action`
- `plan_account`
- `plan_reason`
- `trade_enabled`
- `allow_reason`
- `block_reason`
- `diagnostics`
- `route_enabled`
- `route_frozen_reason`
- `live_position_count`
- `composite_selected_strategy`
- `composite_position_owner`
- `composite_plan_action`
- `composite_position_side`
- `receipt_mode`
- `receipt_accepted`
- `alignment_ok`
- `policy_action`
- `policy_reason`
- `account_metrics`

## account_metrics semantics

`summary.account_metrics` is the current canonical handoff point from runtime into review.

Builder:

- `src/review/account_metrics.py`

Current input sources:

- receipt raw payload performance hints
- optional balance/equity summary pulled from receipt context

Current backward-compatible fields:

- `pnl_usdt`
- `equity_usdt`
- `fee_usdt`

Extended canonical review fields already supported:

- `realized_pnl_usdt`
- `unrealized_pnl_usdt`
- `equity_start_usdt`
- `equity_end_usdt`
- `equity_change_usdt`
- `funding_usdt`
- `max_drawdown_pct`

## Current downstream consumers

Primary downstream consumer chain:

1. `src/review/ingestion.py`
2. `src/review/aggregator.py`
3. `src/review/performance.py`
4. `src/review/report.py`
5. `src/review/export.py`

That means the execution artifact is now the main persistence boundary between runtime and review.

## Canonical vs transitional fields

### Canonical enough today

These are stable enough to depend on operationally:

- artifact file locations
- `summary.plan_*` decision trace summary
- `summary.composite_*` router ownership summary
- `compare_snapshot`
- `summary.account_metrics.fee_usdt`
- `summary.account_metrics.pnl_usdt`
- `summary.account_metrics.equity_usdt`

### Still transitional / improving

These should be treated as evolving semantics rather than final truth:

- realized vs unrealized pnl split accuracy
- funding source completeness
- equity start/end semantics across long review windows
- max drawdown semantics

## Why this path exists

The artifact design intentionally favors:

- append-only JSONL history
- compact review-facing summaries
- forward-compatible extension of performance fields

Instead of coupling review directly to runtime internals every time a new metric is added, the artifact acts as the durable translation layer.

## Operator usage

Use `latest-execution-cycle.json` when:

- diagnosing the most recent cycle
- checking current routing or block reason
- checking the latest account_metrics payload

Use `execution-cycles.jsonl` when:

- generating weekly/monthly/quarterly reviews
- debugging a time series of router or account behavior
- auditing repeated failures or shifts in routing logic

## Current gaps

The biggest remaining gaps in this layer are:

- more explicit canonical performance semantics for realized/unrealized pnl
- stronger funding ingestion
- optional convenience indexes/pointers for latest review-compatible spans

## Related docs

- `docs/state-and-artifacts.md`
- `docs/review-architecture.md`
- `docs/router-composite.md`
- `docs/review-operations.md`

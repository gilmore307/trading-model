# Execution Artifacts

_Last updated: 2026-03-20_

## Purpose

Execution artifacts are the persistence boundary between:
- runtime execution
- later review/report generation
- operator debugging
- historical analysis of execution integrity

## Current artifact files

### Per-account cycle artifacts
Written under:
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

### Parallel-cycle artifacts
Written under:
- `logs/runtime/latest-parallel-execution-cycle.json`
- `logs/runtime/parallel-execution-cycles.jsonl`

## Writer entrypoints

Primary writer module:
- `src/runners/execution_cycle.py`

Key functions:
- `build_execution_artifact(result)`
- `persist_execution_artifact(result)`
- `build_parallel_execution_artifact(result)`
- `persist_parallel_execution_artifact(result)`

## Per-account artifact model

Each per-account artifact contains several important layers.

### 1. Raw execution-cycle payload
Built from `ExecutionCycleResult`.

### 2. Compare/debug snapshot
Stored under:
- `compare_snapshot`

This is still useful transitional metadata, but it is no longer the sole organizing model for live execution.

### 3. Verification snapshot
Stored under:
- `verification_snapshot`

This now records entry verification quality, including fields such as:
- `entry_verified_hint`
- `entry_trade_confirmed`
- `entry_verification_attempt_count`
- `local_position_reason`
- `local_position_status`

### 4. Attribution snapshot
Stored under:
- `attribution_snapshot`

This bridges execution into review/accounting with fields such as:
- `execution_id`
- `client_order_id`
- `order_id`
- `trade_ids`
- ledger leg identifiers
- fee / realized / equity provenance hints

### 5. Summary layer
Stored under:
- `summary`

This is the compact operator/review-facing layer.

It includes things such as:
- runtime mode
- regime
- plan action / account / reason
- route/policy status
- receipt acceptance
- diagnostics
- account metrics
- strategy stats eligibility
- execution recovery markers
- verification quality highlights

## Parallel artifact model

The parallel-cycle artifact records:
- shared regime context
- one nested per-strategy result per account
- entered / accepted / blocked account summaries
- multi-account cycle summary

This is the direction the project is moving toward as the canonical live-cycle structure.

## Canonical direction

### Canonical enough today
- execution artifact file locations
- per-account summary and account metrics fields
- verification snapshot fields
- execution recovery / excluded-trade semantics
- parallel-cycle artifact existence and shape

### Still transitional
- compare/debug/router-composite semantics
- some older field names built around the previous single-route model
- long-window accounting semantics

## Operator usage

Use per-account latest artifacts when:
- diagnosing one account
- checking one account’s latest execution path
- inspecting one account’s verification / reconcile details

Use parallel-cycle artifacts when:
- understanding what all accounts did in the same shared cycle
- debugging multi-account live execution behavior
- preparing future multi-account review/report migration

## Current gaps

The biggest remaining gaps are:
- making parallel artifacts the primary downstream review input
- tightening dry-run/test/live execution-environment isolation
- deeper ID-based attribution and recovery tooling
- stronger canonical realized/unrealized/funding/equity semantics

## Related docs

- `review-architecture.md`
- `multi-account-parallel-execution.md`
- `state-and-artifacts.md`
- `router-composite.md`

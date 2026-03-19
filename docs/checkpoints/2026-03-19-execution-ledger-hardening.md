# 2026-03-19 checkpoint — execution / verification / ledger hardening

## Scope of this checkpoint

This checkpoint captures the main hardening work completed during the 2026-03-19 session on the BTC-only crypto-trading runtime.

Focus areas:

- execution traceability
- verification / reconcile behavior
- ledger / leg accounting
- attribution plumbing
- regression coverage
- config and naming drift cleanup

---

## Major changes completed

### 1. Execution identifier chain added

The runtime now carries a clearer execution identifier chain across submit / state / artifact layers:

- internal `execution_id`
- OKX `client_order_id` / `clOrdId`
- exchange `order_id` / `ordId`
- `trade_ids`

These are now surfaced across:

- execution receipts
- live position state
- execution artifacts
- alerts / notifier output
- attribution snapshot fields

---

### 2. Local position state moved toward leg-based ledgering

The state model was expanded beyond single coarse entry/exit ids.

Added ledger-oriented structures:

- `open_legs`
- `closed_legs`
- `pending_exit`
- FIFO `allocations`

This enables:

- multi-entry positions
- partial exits
- allocation-aware exit accounting
- better reconcile and audit behavior

---

### 3. Duplicate submit / recovery idempotency improved

Added safeguards so repeated calls do not keep mutating local state:

- duplicate entry submissions ignored when execution/order/client-order ids match
- duplicate exit submissions ignored when the same pending exit already exists
- forced exit recovery marking made idempotent

Event history now records these cases explicitly.

---

### 4. Verification behavior substantially improved

Verification moved away from long blocking waits and immediate failure semantics.

Implemented:

- shorter configurable backoff
- immediate initial check before sleeping
- `verification_cycle_timeout`
- cross-cycle verification progression
- pending-verification priority over new submit
- verification-aware reconcile grace window

Current behavior:

- entry/exit can remain in verifying state across cycles
- reconcile no longer immediately freezes during the grace window
- entry timeout can land on `entry_verification_timeout`
- exit timeout can remain `exit_verifying` with explicit timeout reason

### Config closure completed

`verification_cycle_timeout` is now actually injected through runtime initialization:

- `Settings.verification_cycle_timeout`
- `ExecutionPipeline(... settings=...)`
- `RouteController(verification_cycle_timeout=...)`

---

### 5. Partial exit and allocation attribution improved

Partial exit is now a first-class parameter path instead of temporary meta injection:

- `submit_exit(..., requested_size=...)`

Allocation state now tracks:

- `closed_size`
- `trade_ids`
- `fee_usdt`
- `realized_pnl_usdt`

This supports:

- partial exit leg preservation
- multi-allocation exit attribution
- allocation-level fee / realized pnl distribution

Current distribution rule is proportional to closed size within the exit execution.

---

### 6. Artifact and review attribution improved

Added attribution fields into artifact/review flows:

- `attribution_snapshot`
- summary attribution fields
- pending exit allocation attribution in artifacts
- report/export attribution confidence surfacing

Review/export now preserves not only values but also a basic provenance signal.

---

## Config and naming cleanup status

### Fixed / improved

- runtime now treated as BTC-only active trade path by default
- `OkxClient` no longer implicitly falls back to obsolete `breakout`
- new alias env names now preferred:
  - `TREND_ACCOUNT_ALIAS`
  - `CROWDED_ACCOUNT_ALIAS`
- legacy fallback still supported:
  - `BREAKOUT_ACCOUNT_ALIAS`
  - `PULLBACK_ACCOUNT_ALIAS`

### Still intentionally pending / partially migrated

Repo scan still shows old names in several places, including:

- old tests that still explicitly model legacy `breakout/pullback`
- some docs using `BREAKOUT_LOOKBACK` / `PULLBACK_LOOKBACK`
- older architecture notes / framework notes using breakout vocabulary historically
- legacy compatibility env fallback reads in `settings.py`

These are not all bugs, but they are naming debt and should be cleaned further.

---

## Regression coverage added during this session

The following behaviors were added to the test matrix during the session:

- partial exit allocation behavior
- multi-allocation exit attribution
- artifact allocation attribution presence
- entry verification progression
- entry timeout behavior
- exit timeout behavior
- forced recovery idempotency
- pending exit blocks duplicate recovery submit
- recovery + partial exit combo behavior
- timeout + attribution artifact behavior
- settings verification timeout env loading
- pipeline injection of `verification_cycle_timeout`
- new env alias names preferred over legacy fallbacks

---

## Known remaining gaps

### 1. Legacy naming debt still exists

Not fully cleaned yet:

- `breakout_lookback`
- `pullback_lookback`
- some tests and docs still intentionally reference old names

### 2. Allocation attribution is still approximate, not per-fill exact

Current state:

- allocation-level trade ids supported
- allocation-level fee / realized pnl supported
- distribution is proportional by consumed size

Not yet implemented:

- exact per-fill attribution to each allocation
- fine-grained fill-to-leg mapping when a single exit affects multiple legs asymmetrically

### 3. Exchange-first replay is not complete

The system is now much stronger locally, but still does not fully implement:

- exchange event sourcing
- replay from exchange facts as primary truth
- exact historical rebuild from fills/orders alone

### 4. Some recovery orchestration could still be expanded

Especially around:

- more explicit pending-exit reuse semantics
- stronger replay/restart recovery flows
- richer route-freeze / unfreeze integration tests

---

## Suggested next steps

1. continue sweeping legacy breakout/pullback naming debt
2. add tests for route freeze / verification grace interactions
3. improve multi-allocation exact fill distribution beyond proportional approximation
4. continue moving toward exchange-first replay and stronger recovery orchestration

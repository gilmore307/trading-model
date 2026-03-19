# Research / Runtime Separation

_Last updated: 2026-03-20_

## Goal

Keep **historical validation / research** and **live runtime execution** as two clearly separated systems that can share pure logic, but do not depend on each other operationally.

In short:

- historical research must not require `trade_daemon`
- live runtime must not require research runners to function
- both paths may reuse pure regime / strategy / evaluation logic
- persistence, orchestration, and entrypoints should remain separate

## Why this matters

If research depends on live runtime artifacts too tightly, then:

- historical validation becomes slow and awkward
- offline backtests inherit operational assumptions from live trading
- it becomes hard to test old data without current-time context
- the research path cannot evolve into a raw historical replay engine cleanly

If live runtime depends on research machinery too much, then:

- daemon complexity increases
- operational reliability is hurt by research-only code paths
- safety boundaries become less clear

## Desired architecture

### 1. Shared pure logic

These are allowed to be shared:

- regime classification logic
n- router decision logic
- strategy executor logic
- forward-label helpers
- research evaluators
- report rendering helpers

Rule:
- shared logic should be pure or near-pure where possible
- no daemon-only side effects inside shared logic

### 2. Live runtime path

Entry:
- `src/runners/trade_daemon.py`

Responsibilities:
- fetch current market/exchange state
- run execution pipeline
- reconcile local/exchange state
- place demo/live orders when allowed
- persist runtime artifacts
- send operational notifications

Outputs:
- `logs/runtime/*`
- execution artifacts
- latest regime / latest cycle snapshots

Must not require:
- offline research runners
- historical replay inputs
- batch report generation to complete a cycle

### 3. Historical research path

Entries:
- `src/runners/backtest_research.py`
- future raw historical replay runner(s)

Responsibilities:
- load historical data
- build research rows / datasets
- generate forward labels
- run regime / strategy / parameter evaluation
- export research reports

Outputs:
- `logs/research/*`
- backtest dataset jsonl
- research report json / markdown

Must not require:
- running daemon
- runtime lock/pid files
- Discord notifier
- exchange execution adapters
- current wall-clock continuity

## Current state

### Already separated enough

- `trade_daemon.py` runs independently as a live runtime loop
- `backtest_research.py` can run independently from historical snapshot jsonl
- research reports can be generated without daemon uptime
- review/report runners are callable as normal Python entrypoints

### Still too coupled / transitional

1. offline research currently still prefers **snapshot-based** input instead of raw market replay input
2. some research row generation still rebuilds from `RegimeRunnerOutput`, which was originally shaped for live runtime
3. research path currently still benefits from runtime-style snapshot structure instead of a dedicated raw replay schema
4. reevaluation / parameter-preview path needs hardening before being treated as stable research output

## Separation rules going forward

### Rule 1: no research-only dependencies in the daemon critical loop
Do not make `trade_daemon` depend on:
- research report generation
- parameter search preview
- backtest-only runners
- batch historical replay logic

### Rule 2: research runners must accept explicit historical inputs
Research runners should accept:
- raw historical market data, or
- standardized offline snapshot files

and should not require:
- currently running daemon state
- current runtime lock state
- live notifier availability

### Rule 3: artifact compatibility is allowed, operational dependence is not
It is fine for research to consume runtime artifacts.
It is **not** fine for research to require runtime to be active.

### Rule 4: raw historical replay is the next separation milestone
The next major milestone is:

- ingest raw market history
- rebuild feature timeline
- rerun classifier/router/executor logic offline
- produce research rows without going through live execution persistence

## Current priority checklist

### P1
- design raw historical replay input schema
- define minimal replay builder data flow
- harden reevaluation / parameter-preview path

### P2
- run offline research on historical snapshot data regularly
- accumulate real forward-labeled runtime samples for comparison

### P3
- compare snapshot-based offline results vs live runtime-derived results
- make sure both paths agree on shared logic outputs where expected

## Completion standard

We can say the separation is materially successful when:

1. daemon can run continuously with no research runner dependency
2. historical research can run from historical inputs with no daemon dependency
3. raw historical replay can produce research rows directly
4. shared logic is reused without mixing operational side effects into offline paths

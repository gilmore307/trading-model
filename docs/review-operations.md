# Review Operations

This document is the operator/runbook entry for the review pipeline.

## Current scope

The project now has a first usable review artifact pipeline with:

- canonical performance ingestion from execution artifacts
- execution-history aggregation
- weekly/monthly/quarterly review report generation
- JSON + Markdown export under `reports/trade-review/`

Current operating assumption:

- live trading runs one real account on the latest promoted strategy version
- the trade daemon is a separate long-running process and should keep running during review generation
- live review is for execution + realized-result diagnostics
- live review is not the primary parameter-optimization loop
- historical backtest / research remains the optimization line

## Primary artifact source

Execution history is read from:

- `logs/runtime/execution-cycles/YYYY-MM-DD.jsonl` UTC daily partitions

Review reports are written to:

- `reports/trade-review/`

Convenience files maintained automatically:

- `latest_weekly.json` / `latest_weekly.md`
- `latest_monthly.json` / `latest_monthly.md`
- `latest_quarterly.json` / `latest_quarterly.md`
- `index.json` — rolling report index with latest-by-cadence pointers

## Strategy-upgrade review

This is now the canonical live-operations review trigger.

Primary intent:
- validate the effect of a newly promoted strategy / parameter version
- review theoretical-signal vs actual-execution deviations
- review execution quality, position drift, and operational anomalies
- keep trading running while validation is generated; the review is attached to the same promotion-triggered strategy upgrade event and does not force daemon mode switches

Run the unified strategy-upgrade event runner:

```bash
./.venv/bin/python -m src.runners.strategy_upgrade_event
```

Optional helper cleanup:

```bash
./.venv/bin/python -m src.runners.strategy_upgrade_event --destructive
```

Trigger rule:

- run this when historical backtest / research promotes a new active strategy version
- trade daemon should detect the new pointer, keep running, and attach runtime artifacts to the new version immediately
- trade daemon should also emit a `strategy_upgrade_event_requested` record when it sees the version change; the heavier upgrade validation path can then run separately without blocking trading
- the upgrade event then combines helper/calibration work with upgrade validation review

## Position handling during strategy upgrade

If a live position exists when the active strategy version changes, do not stop the daemon just to "make the upgrade clean".

Use strategy-switch handling instead:

- keep trade running on the new active version immediately
- treat any existing live position under the same logic used for strategy switching / ownership transition
- if the new active strategy wants to keep/own the position, continue managing it under the new strategy context
- if the new active strategy wants to close-and-wait, let the normal execution/switch path unwind it rather than forcing a separate upgrade-time stopout
- record the upgrade request even when a position is open; open position is not a blocker for the strategy-upgrade event

This keeps upgrade handling aligned with the normal strategy-switch logic rather than introducing a separate stop-the-world position policy only for upgrades.

Current consumer/result observation should include, when available:

- whether open positions existed at upgrade-request processing time
- current position owner / route metadata
- which strategy-switch handling policy applied
- a minimal handover decision such as `no_open_position`, `transfer_ownership`, or `close_and_wait`
- a matching handover marker persisted for later audit / state inspection

Current minimal out-of-band processing path:

- daemon writes `logs/runtime/latest-strategy-upgrade-request.json`
- an external consumer can run:

```bash
./.venv/bin/python -m src.runners.process_strategy_upgrade_request
```

- that consumer reads the latest request and executes the unified `strategy_upgrade_event`
- the consumer also writes a minimal state-level handover marker to `logs/runtime/latest-strategy-handover-marker.json`

## Monthly review

This is an aggregate live-operations summary, not the main parameter-discussion layer.

Generate a monthly review anchored to a UTC timestamp:

```bash
./.venv/bin/python scripts/scripts_monthly_review.py --now 2026-03-15T12:00:00+00:00
```

Optional explicit previous boundary:

```bash
./.venv/bin/python scripts/scripts_monthly_review.py \
  --now 2026-03-15T12:00:00+00:00 \
  --previous-review-end 2026-02-01T00:00:00+00:00
```

Window rule:

- monthly review currently covers start-of-previous-UTC-month -> start-of-current-UTC-month
- output label format: `monthly:START->END`

## Quarterly review

This is a structural live-operations / execution-system review layer.

Generate a quarterly review anchored to a UTC timestamp:

```bash
./.venv/bin/python scripts/scripts_quarterly_review.py --now 2026-05-15T12:00:00+00:00
```

Optional explicit previous boundary:

```bash
./.venv/bin/python scripts/scripts_quarterly_review.py \
  --now 2026-05-15T12:00:00+00:00 \
  --previous-review-end 2026-01-01T00:00:00+00:00
```

Window rule:

- quarterly review currently covers start-of-previous-UTC-quarter -> start-of-current-UTC-quarter
- output label format: `quarterly:START->END`

## Output contents

Each review export produces:

- one JSON artifact
- one Markdown artifact

The report currently contains:

- executive summary
- recommended actions
- realized live-performance summary
- execution-quality / deviation sections
- section status summary

## Operator note

`review` and `calibrate` should be understood as event/helper concepts, not daemon runtime modes.

Use the unified `strategy_upgrade_event` as the primary operator entry when a new promoted strategy version is adopted in live trading.

## Operational intent

The review path is being built so that the trading core stays portable while OpenClaw remains an orchestration/operator layer.

That means:

- the report generation itself should remain callable as normal Python runners
- OpenClaw cron / session orchestration may trigger it
- future non-OpenClaw schedulers should be able to call the same runner scripts unchanged

## Related documents

- `docs/review-automation.md` — scheduling / deployment / OpenClaw-vs-non-OpenClaw automation notes

## Near-term next steps

- improve canonical realized/unrealized/funding semantics
- add report index / latest-pointer convenience files
- remove or downgrade multi-account / compare / router-composite live-review assumptions
- document exact promotion-to-upgrade-event orchestration examples

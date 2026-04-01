# Runtime and Modes

## Goal

Document the runtime mode model and operational meaning of each mode.

## Modes and events

- `develop` — idle development / maintenance mode; do not run normal strategy execution or routing
- `trade` — normal trading mode; the only mode that runs normal strategy routing and real execution
  - runtime check: only verify enough available USDT margin before a real entry
- `reset` — development-only destructive reset: flatten, verify flat, convert residual assets if needed, rebuild/reset local bucket state, then auto-return to `develop`
- `test` — dedicated execution-system test mode; does not run normal strategy logic and should return to `develop`
  - workflow: fixed demo-only stress cycle on the configured test symbol/account
  - default pattern: entry -> add(s) -> exit, repeated for `TEST_CYCLES`
  - safeguard: refuses to run unless `OKX_DEMO=true`

## Events / jobs

- `strategy_upgrade_event` — the main promotion-triggered event; when the active strategy version changes, trade keeps running, helper/calibration actions may run, and upgrade validation/review is emitted around the same upgrade event
- `review` / `calibrate` — legacy sub-steps / compatibility labels inside the broader strategy-upgrade event; they should not be treated as standalone runtime modes

## User terminology

- **strategy upgrade event** = promotion-triggered online upgrade handling: detect new active strategy, run helper/calibration steps if needed, and emit upgrade validation review while trade continues running
- **calibrate** = legacy shorthand for the helper/baseline-refresh portion of the strategy upgrade event
- **reset** = destructive development reset that clears historical/runtime state, then return to `develop`

## Current operating interpretation

- live trading now assumes a **single real account running the current promoted strategy version**
- `trade` should be a long-running daemon that keeps running during strategy-upgrade events and any attached validation/report steps
- strategy changes should be hot-loaded from the latest promoted strategy artifacts rather than requiring a stop-the-world review/calibrate/trade sequence
- when trade detects an active-strategy version change, it should at minimum emit a `strategy_upgrade_event_requested` record so the upgrade-validation path can run out-of-band without stopping live execution
- live upgrade validation is no longer time-driven first; it is primarily promotion-triggered
- historical backtest / research is the optimization line for:
  - new instruments
  - new families
  - new variants
  - ranking / promotion / archival
  - parameter changes
- live `review` should focus on:
  - realized live pnl/equity summaries
  - theoretical-signal vs actual-execution deviations
  - order / position / sync health
  - execution-layer improvements

## Current state

- Mode system is active and durable.
- `review` / `calibrate` should be treated as event/job concepts only; they are no longer valid runtime modes in the enum / policy layer.
- This is a core project concept and should stay synchronized with runtime implementation.

## Next step

Keep this file updated whenever mode semantics or auto-transitions change.

# Runtime and Modes

## Goal

Document the runtime mode model and operational meaning of each mode.

## Modes

- `develop` — idle development / maintenance mode; do not run normal strategy execution or routing
- `trade` — normal trading mode; the only mode that runs normal strategy routing and real execution
  - runtime check: only verify enough available USDT margin before a real entry
  - do not decide whether to run `calibrate` inside normal trade execution; `calibrate` is the fixed gate after `review`
- `review` — review/report generation mode; runs review artifacts only, then auto-transitions into `calibrate`
- `calibrate` — weekly operational flow: flatten, verify flat, convert non-USDT assets to USDT, verify startup capital, reset local buckets, then auto-return to `trade`
- `reset` — development-only destructive reset: flatten, verify flat, convert residual assets if needed, rebuild/reset local bucket state, then auto-return to `develop`
- `test` — dedicated execution-system test mode; does not run normal strategy logic and should return to `develop`
  - workflow: fixed demo-only stress cycle on the configured test symbol/account
  - default pattern: entry -> add(s) -> exit, repeated for `TEST_CYCLES`
  - safeguard: refuses to run unless `OKX_DEMO=true`

## User terminology

- **calibrate** = normal post-flatten weekly bucket reset for operations, then return to `trade`
- **reset** = destructive development reset that clears historical/runtime state, then return to `develop`

## Current state

- Mode system is active and durable.
- This is a core project concept and should stay synchronized with runtime implementation.

## Next step

Keep this file updated whenever mode semantics or auto-transitions change.

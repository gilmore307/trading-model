# Runtime and Modes

## Goal

Document the runtime mode model and operational meaning of each mode.

## Modes

- `develop` — development / debugging mode; should not intentionally progress into normal trading workflows
- `trade` — normal trading mode
- `review` — review/report generation mode; completes into `calibrate`
- `calibrate` — weekly operational flow: flatten, convert to USDT, reset local buckets, then auto-return to `trade`
- `reset` — development-only destructive reset: backup + clear runtime/history artifacts + rebuild buckets, then auto-return to `test`
- `test` — buffer-funded stress test mode on fixed test symbol `XRP-USDT-SWAP`, routed through the Breakout account, then auto-return to `develop`

## User terminology

- **calibrate** = normal post-flatten weekly bucket reset for operations, then return to `trade`
- **reset** = destructive development reset that clears historical/runtime state, then return to `develop`

## Current state

- Mode system is active and durable.
- This is a core project concept and should stay synchronized with runtime implementation.

## Next step

Keep this file updated whenever mode semantics or auto-transitions change.

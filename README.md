# openclaw-automation

OKX demo trading automation scaffold for same-day demo testing.

## Scope
- Exchange: OKX perpetual swaps
- Environment: demo / simulated trading only
- Symbols: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
- Strategies: breakout, pullback, meanrev
- Notifications: sent via OpenClaw's configured Discord channel

## Current status
This project now supports:
- config loading from `.env`
- demo-safe exchange connectivity checks
- multi-strategy evaluation across BTC/ETH/SOL
- per-strategy-per-symbol budget buckets
- entry + exit state transitions
- dry-run execution with state persistence
- optional OKX demo order submission path
- test coverage for signal / risk / state / bucket wiring

It is still **demo-only** and still **not ready for unattended real-money trading**.

## Environment
Expected in `.env`:
- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSPHRASE`
- `OKX_DEMO=true`

Optional:
- `OPENCLAW_DISCORD_CHANNEL`
- `SYMBOLS=BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP`
- `STRATEGIES=breakout,pullback,meanrev`
- `TIMEFRAME=5m`
- `BREAKOUT_LOOKBACK=20`
- `PULLBACK_LOOKBACK=20`
- `MEANREV_LOOKBACK=20`
- `MEANREV_THRESHOLD=0.015`
- `MAX_OPEN_POSITIONS=2`
- `SIGNAL_COOLDOWN_BARS=12`
- `BUCKET_INITIAL_CAPITAL_USDT=500`
- `DEFAULT_ORDER_SIZE_USDT=100`
- `DRY_RUN=true`

## Run
```bash
source .venv/bin/activate
python -m src.runner.live_trader --check
python -m src.runner.live_trader
```

## Modes
- `develop` — development / debugging mode; should not intentionally progress into normal trading workflows
- `trade` — normal trading mode
- `review` — review/report generation mode; completes into `calibrate`
- `calibrate` — weekly operational flow: flatten, convert to USDT, reset local buckets, then auto-return to `trade`
- `reset` — development-only destructive reset: backup + clear runtime/history artifacts + rebuild buckets, then auto-return to `test`
- `test` — buffer-funded stress test mode on fixed test symbol `XRP-USDT-SWAP`, routed through the Breakout account, then auto-return to `develop`

To simulate a run **without** persisting state:
```bash
python -m src.runner.live_trader --no-state-write
```

To allow actual OKX **demo** submissions:
```bash
# keep OKX_DEMO=true
# set DRY_RUN=false in .env
python -m src.runner.live_trader --arm-demo-submit
```

To run tests:
```bash
pytest -q
```

## State
State is stored at:
- `~/openclaw-automation/logs/state.json`

Tracked state includes:
- open positions keyed as `strategy:symbol`
- last signal per strategy/symbol bucket
- per-bucket capital (`initial_capital_usdt`, `available_usdt`, `allocated_usdt`)
- execution history

## Exit behavior
- If a bucket has an open position and its current strategy signal turns `flat`, the runner closes that tracked demo position.
- If a bucket has an open position and the strategy flips to the opposite side, the runner first closes the existing tracked position.
- In demo-submit mode, exit orders are sent as reduce-only market orders using the tracked contract amount from the entry.

## Safety
- Designed for OKX demo trading first.
- Refuses to run if `OKX_DEMO` is not truthy unless code is explicitly changed.
- Default mode is `DRY_RUN=true`.
- `--arm-demo-submit` alone does not arm execution; config must also set `DRY_RUN=false`.
- Current execution path is still a controlled demo scaffold, not a full production order-management system.
- No real trading path was added.

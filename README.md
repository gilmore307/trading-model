# crypto-trading

虚拟币交易系统重构工作区。当前处于重做阶段，旧的 OKX demo 交易脚手架已不再作为目标架构。

## Scope
- Exchange: OKX perpetual swaps
- Environment: demo / simulated trading only
- Symbols: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
- Strategies: breakout, pullback, meanrev
- Notifications: sent via OpenClaw's configured Discord channel

## Core status
### What this project is
- OKX perpetual demo/simulated trading rebuild
- execution + state + review/reporting stack under active reconstruction
- still **not ready for unattended real-money trading**

### Core capabilities already in place
- config loading from `.env`
- multi-strategy evaluation across BTC/ETH/SOL
- per-strategy-per-symbol budget buckets
- entry/exit state transitions
- dry-run state persistence
- optional OKX demo order submission path
- route/state reconciliation before normal cycle actions
- execution artifact persistence under `logs/runtime/`
- review/report scaffolding with history aggregation from `execution-cycles.jsonl`
- canonical review metric ingestion path for fee data, with pnl/equity hooks prepared

### Current priority
- finish full canonical performance production into `summary.account_metrics`, with `realized_pnl_usdt` / `unrealized_pnl_usdt` / `equity_end_usdt` preferred over legacy compatibility mirrors
- continue making every important node traceable in Markdown

## Documentation map
- `CURRENT_STATE.md` — fast-resume spine / current handoff status
- `PROJECT_STATUS.md` — project-level status and major milestones
- `TRACEABILITY.md` — documentation rule and traceability standard
- `docs/project-map.md` — high-level project orientation map
- `docs/execution-artifacts.md` — execution artifact writer/fields/downstream-consumer map
- `docs/review-architecture.md` — review pipeline architecture and boundaries
- `docs/router-composite.md` — router-composite / ownership / compare-snapshot model
- `docs/review-operations.md` — review runner / export / report operations runbook
- `docs/review-automation.md` — scheduling / deployment / automation notes for review jobs
- `docs/regime-and-decision-flow.md` — layered regime / route / execution gating model
- `docs/known-gaps-and-boundaries.md` — realism boundary / current transitional semantics
- `reports/review-ingestion-status.md` — review/performance ingestion status

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

## Review runners
```bash
./.venv/bin/python scripts_weekly_review.py --now 2026-03-15T12:00:00+00:00
./.venv/bin/python scripts_monthly_review.py --now 2026-03-15T12:00:00+00:00
./.venv/bin/python scripts_quarterly_review.py --now 2026-05-15T12:00:00+00:00
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
- `/root/.openclaw/workspace/projects/crypto-trading/logs/state.json`

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

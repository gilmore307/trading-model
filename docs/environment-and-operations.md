# Environment and Operations

_Last updated: 2026-03-20_

## Environment

Expected in `.env`:
- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSPHRASE`
- `OKX_DEMO=true`

Important runtime controls:
- `DRY_RUN=true|false`
- `SYMBOLS=BTC-USDT-SWAP`
- `STRATEGIES=trend,crowded,meanrev,compression,realtime`
- `DEFAULT_ORDER_SIZE_USDT=...`
- `BUFFER_CAPITAL_USDT=...`

Other common tunables:
- `TIMEFRAME=5m`
- `TREND_LOOKBACK=20`
- `CROWDED_LOOKBACK=20`
- `MEANREV_LOOKBACK=20`
- `MEANREV_THRESHOLD=0.015`
- `MAX_OPEN_POSITIONS=2`
- `SIGNAL_COOLDOWN_BARS=12`
- `BUCKET_INITIAL_CAPITAL_USDT=500`

Optional notifications/config:
- `OPENCLAW_DISCORD_CHANNEL`
- `NOTIFY_RUNTIME_WARNINGS=false`

## Main run paths

### One bounded cycle
```bash
./.venv/bin/python -m src.runners.trade_daemon --max-cycles 1
```

### Normal daemon startup
```bash
./run_daemon.sh
```

### systemd-managed runtime
```bash
systemctl status crypto-trading.service --no-pager -n 40
systemctl restart crypto-trading.service
```

## Review scripts

```bash
./.venv/bin/python scripts/review/weekly_review.py --now 2026-03-15T12:00:00+00:00
./.venv/bin/python scripts/review/monthly_review.py --now 2026-03-15T12:00:00+00:00
./.venv/bin/python scripts/review/quarterly_review.py --now 2026-05-15T12:00:00+00:00
```

## Historical data fetch

```bash
./.venv/bin/python scripts/data/fetch_okx_history_candles.py --inst-id BTC-USDT --bar 1m --pages 10
```

## Tests

```bash
./.venv/bin/python -m pytest -q
```

## Operating notes

- project scripts now live under `scripts/`
- project docs now live under `docs/`
- runtime/research artifacts should live under `logs/` or `reports/`, not as loose Markdown in the repo root

## Safety

- designed for OKX demo trading first
- no real-money path should be implied by current docs
- current execution path is still under active hardening
- dry-run vs live-trade state isolation still needs tightening
- when investigating execution anomalies, prefer stopping the daemon first, then repairing exchange/local state, then restarting cleanly

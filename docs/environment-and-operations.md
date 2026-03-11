# Environment and Operations

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

## Demo submit

```bash
# keep OKX_DEMO=true
# set DRY_RUN=false in .env
python -m src.runner.live_trader --arm-demo-submit
```

## Tests

```bash
pytest -q
```

## Safety

- Designed for OKX demo trading first.
- Refuses to run if `OKX_DEMO` is not truthy unless code is explicitly changed.
- Default mode is `DRY_RUN=true`.
- `--arm-demo-submit` alone does not arm execution; config must also set `DRY_RUN=false`.
- Current execution path is still a controlled demo scaffold, not a full production OMS.
- No real trading path was added.

# crypto-trading final framework

## 1. Objective
The system does not try to find one universally best strategy.
It first decides what kind of market environment BTC is currently in, then routes execution to the strategy account best matched to that environment.

The historical runtime modes are preserved in v2:
- `develop`
- `test`
- `trade`
- `calibrate`
- `reset`

Core idea:
- classify regime first
- trade second
- allow explicit no-trade state
- use machine learning later mainly for regime recognition and confidence estimation

---

## 2. Trading scope
- Instrument: `BTC-USDT-SWAP`
- Venue: OKX demo first
- Phase goal: architecture-first rebuild, not old-system patching

---

## 3. Regime names vs account names
These are intentionally different.

### Regimes (market environments)
- `trend`
- `range`
- `compression`
- `crowded`
- `shock`
- `chaotic`

### Strategy accounts
- `trend`
- `meanrev`
- `compression`
- `crowded`
- `realtime`

### Routing table
- `trend` -> `trend`
- `range` -> `meanrev`
- `compression` -> `compression`
- `crowded` -> `crowded`
- `shock` -> `realtime`
- `chaotic` -> no account / no-trade

---

## 4. Regime classification logic
The classifier is not flat. It is priority-based.

### Layer 1: event override
Highest priority.
If short-horizon market behavior looks like shock / liquidation / dislocation, classify as `shock` first.

Typical inputs:
- 1m realized volatility percentile
- 1m volume percentile
- short-window liquidation notional percentile
- short-window order book imbalance spike
- fast VWAP dislocation + reclaim

### Layer 2: crowding override
If not `shock`, check whether derivatives positioning is excessively crowded.
If yes, classify as `crowded` before ordinary technical states.

Typical inputs:
- funding percentile or z-score
- open interest percentile and acceleration
- basis percentile
- medium-horizon price extension

### Layer 3: ordinary regime classification
If neither shock nor crowding dominates, classify among:
- `trend`
- `range`
- `compression`
- `chaotic`

This layer is score-based, not brittle single-threshold if/else.
Current v1 ordering is:
- compute TrendScore / RangeScore / SqueezeScore
- choose the top regime only if the top score is high enough and clearly above the runner-up
- otherwise fall back to `chaotic`

---

## 5. Regime score families
### TrendScore
- ADX strength
- EMA20 / EMA50 slope alignment
- breakout persistence
- HH/LL continuation structure
- one-sided closes vs EMA20

### RangeScore
- low ADX score
- VWAP / middle-band crossing frequency
- range stability
- false-breakout ratio

### SqueezeScore
- Bollinger bandwidth low percentile
- realized volatility low percentile
- ATR low percentile
- range narrowing speed

### CrowdingScore
- funding percentile / z-score
- OI percentile
- basis percentile
- price extension score

### ShockScore
- 1m volatility burst
- 1m volume/trade burst
- liquidation anomaly
- order book imbalance anomaly
- fast VWAP dislocation

### v1 decision order
1. `ShockScore` high -> `shock`
2. `CrowdingScore` high -> `crowded`
3. compare `TrendScore`, `RangeScore`, `SqueezeScore`
4. if confidence is weak or top scores are too close -> `chaotic`

### Chaotic detection
`chaotic` is inferred from uncertainty, for example:
- all scores low
- top score below activation threshold
- top1 vs top2 too close
- regime flips too frequently
- confirmation failure rate elevated

---

## 6. Timeframe hierarchy
### 4h background layer
Used for macro trend / structure context.
It should influence but not always directly override the main classification.
Feature emphasis:
- higher-timeframe ADX/trend structure
- higher-timeframe EMA slope alignment
- higher-timeframe VWAP/extension context

### 15m primary classification layer
Main regime decision layer for ordinary conditions.
Most non-event regime labels come from here.
Feature emphasis:
- ordinary trend/range/compression structure
- 15m volatility and bandwidth state
- 15m reversion context

### 1m event override layer
Used for fast anomaly detection.
It can temporarily override the 15m main regime and mark the market as `shock`.
Feature emphasis:
- short-horizon realized volatility burst
- liquidation spike intensity
- order-book imbalance
- fast VWAP dislocation context

---

## 7. Unified market data hub
The system uses one shared ingestion backbone, not separate ad-hoc data pulls per strategy.

### Principle
One market data hub -> multiple strategy-specific derived views.

Do not do either of these:
- separate fully independent data pipelines per strategy
- forcing every strategy to decide directly on the same high-frequency raw microstructure feed

Correct design:
- unified raw ingestion
- shared derived state
- different strategy views for different abstraction levels

### Raw inputs expected
- bars: 1m / 5m / 15m / 1h / 4h
- ticker / last / bid / ask / mark / index
- funding
- current OI
- OI history
- basis
- recent trades
- liquidation events
- book top / order book imbalance

### Derived views
- trend view
- range / mean reversion view
- compression view
- crowded view
- shock / realtime view

---

## 8. Strategy cadence targets
### trend account
- trade horizon: 6h to 3d
- formal decision cadence: 1h close
- background filter: 4h
- risk refresh: 1s to 5s
- execution staging: `watch -> arm -> enter`

### meanrev account
- trade horizon: 15m to 6h
- formal decision cadence: 5m to 15m
- bars updated continuously
- risk refresh: 1s to 3s
- execution staging: `watch -> arm -> enter`

### compression account
- trade horizon: 30m to 12h
- formal decision cadence: 15m
- OI / basis refresh: 30s to 60s
- risk refresh: 1s to 3s
- execution staging: `watch -> arm -> enter`

### crowded account
- trade horizon: 5m to 2h
- formal decision cadence: 1m to 5m
- mark price refresh: 1s
- current OI refresh: 5s to 15s
- OI / basis history refresh: 1m to 5m
- execution staging: `watch -> arm -> enter`

### realtime account
- trade horizon: 10s to 10m
- decision cadence: event-triggered
- bookTicker: real-time
- depth / aggTrade: high-frequency
- liquidation / force-order snapshots: sub-minute
- mark price: 1s
- execution staging: `watch -> arm -> enter`

### chaotic state
- no new trade
- periodic re-check only

---

## 9. Execution architecture
Two execution families, gated by runtime mode.

### Minute engine
Handles:
- trend
- range -> meanrev account
- compression
- crowded

Characteristics:
- bars and features update continuously
- formal trade decisions happen on their own cadence
- risk control updates faster than trade decision cadence

### Realtime engine
Handles:
- shock -> realtime account

Characteristics:
- event-driven
- lower-latency trigger path
- tighter anti-duplicate, debounce, in-flight lock, slippage guard

---

## 10. State model
The state layer should track:
- active regime
- regime confidence
- recent reasons for classification
- per-account positions and exposure
- last route decision
- no-trade / chaotic flag
- realtime override active or not

### Live position integrity rules
- do not mark entry as `open` without exchange position confirmation
- do not mark exit as `flat` without exchange flat confirmation
- only live statuses participate in alignment (`entry_submitted`, `entry_verifying`, `open`, `exit_submitted`, `exit_verifying`)
- `reconcile_mismatch` is an exception state, not a live tradable state

---

## 11. Machine learning role
Machine learning is not phase-1 core execution logic.
Primary role later:
- regime classification
- regime transition prediction
- confidence estimation

Not the first target:
- direct price prediction
- blind strategy parameter optimization without regime context

---

## 11. Runtime modes
### develop
- strategy and regime logic allowed
- execution forced to dry-run

### test
- constrained validation mode
- currently treated as dry-run-first in skeleton

### trade
- normal strategy routing and execution allowed

### calibrate
- blocks normal routing
- workflow includes: flatten all positions -> verify flat -> reset bucket state
- non-destructive weekly operational reset
- should auto-return to `trade`

### reset
- blocks normal routing
- workflow includes: flatten all positions -> verify flat -> reset bucket state
- destructive development reset / clean-start workflow
- should auto-return to `develop`

## 12. Build order
### Phase 1
- rename and stabilize regime vocabulary
- market data hub
- BTC-only ingestion
- feature engine v1
- rule-based classifier v1
- layered classifier structure: 4h background / 15m primary / 1m shock override
- minimal BTC regime runner (`ingest -> features -> classify -> route`)
- optional shock-enhanced runner window using live public WS events

### Phase 2
- minute engine for trend / range / compression / crowded
- chaotic/no-trade support
- account-aware state and routing
- live position state machine
- live state store
- route controller
- execution pipeline skeleton (`regime -> route -> submit/verify/reconcile/policy`)
- exchange snapshot provider for real local-vs-exchange verification
- execution adapter abstraction (dry-run first, exchange-backed later)
- per-regime executor / plan layer
- route freeze / enable registry
- reconciliation / alignment layer
- entry/exit verification flow
- calibrate/reset workflow skeleton (`flatten -> verify flat -> reset bucket state -> auto transition`)
- OKX-backed workflow hooks for flatten / verify flat / bucket reset

### Phase 3
- shock override logic
- realtime engine
- stronger derivatives / crowding features

### Phase 4
- ML overlay
- replay / audit improvements
- dashboard refinement
- periodic review framework (weekly / monthly / quarterly)

---

## 14. Review framework
### Weekly review
Run every Sunday.
Review window:
- previous Saturday 00:00 UTC
- to current Saturday 00:00 UTC

Purpose:
- compare the always-on strategy accounts
- compare `router_composite` and `flat_compare`
- review fee burden / trading frequency
- produce small calibration candidates

Allowed adjustment style:
- small threshold / cooldown / frequency tuning
- avoid structural strategy changes

### Monthly review
Run on the first Sunday of each month.
Review window:
- previous monthly review boundary
- to current monthly review boundary

Purpose:
- multi-week strategy stability review
- strategy-internal parameter discussion
- router/composite attribution-aware comparison
- regime-recognition quality review

Allowed adjustment style:
- strategy-internal parameter tuning
- generate recommendations first, usually confirm before applying to live trading behavior

### Quarterly review
Run on the first Sunday every three months.
Review window:
- previous quarterly review boundary
- to current quarterly review boundary

Purpose:
- structural review of strategy fitness
- regime taxonomy review
- review/risk framework review
- ML/RL roadmap review

Allowed adjustment style:
- structural changes may be discussed here
- preserve auditability and comparability across periods

### ML / RL role in review
Planned learning direction:
- build a learning system for market/regime recognition
- use weekly/monthly review outputs as calibration feedback
- use monthly review as the primary layer for internal parameter discussion
- reserve stronger RL/policy-learning usage for later router/meta-policy stages rather than immediate raw price prediction

---

## 13. Final summary
`crypto-trading` is a BTC-first, regime-routed trading architecture:
- one shared market data hub
- 4h background + 15m primary classification + 1m event override
- regimes named by market structure
- accounts named by execution role
- explicit no-trade state when structure is unclear

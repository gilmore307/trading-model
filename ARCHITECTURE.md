# crypto-trading architecture

## Goal
Build a regime-routed crypto trading system that:
- classifies the current market regime first
- routes capital to the strategy account best matched to that regime
- treats `no-trade` as a first-class system state
- supports both minute-level and real-time execution paths

## Scope for current implementation
- Active trade asset universe: `BTC-USDT-SWAP` only
- Exchange: OKX demo first
- Note: `ETH-USDT-SWAP` / `SOL-USDT-SWAP` remain framework-reserved symbols, not the current active trade path
- Strategy accounts:
  - `trend`
  - `meanrev`
  - `compression`
  - `crowded`
  - `realtime`
- Regimes:
  - `trend`
  - `range`
  - `compression`
  - `crowded`
  - `shock`
  - `chaotic`

---

## Regime model
The system classifies market state into exactly one primary regime at a time.

### Tradable regimes
1. `trend`
   - trend continuation / directional expansion
   - routed account: `trend`
2. `range`
   - bounded range / reversion to mean
   - routed account: `meanrev`
3. `compression`
   - volatility compression / energy build-up
   - routed account: `compression`
4. `crowded`
   - extreme one-sided positioning / squeeze risk
   - routed account: `crowded`
5. `shock`
   - event shock / liquidation / order-book dislocation
   - routed account: `realtime`

### Non-tradable regime
6. `chaotic`
   - transition / low-confidence / conflicting signals
   - execution family: none
   - action: no new trades, optionally flatten risk depending on policy

---

## Core design principle
Do **not** optimize a single universal strategy first.

Instead:
1. observe market state
2. classify regime
3. choose the strategy account mapped to that regime
4. trade only if confidence is high enough
5. stay flat when confidence is low or the regime is `chaotic`

---

## System layers

### 1. Market ingestion
Responsible for collecting market inputs with higher frequency than decision cadence.

A single **Market Data Hub** owns raw feed ingestion and exposes multiple strategy-specific views.

#### Minute-path ingestion
- target refresh: every `10s` or `15s`
- inputs:
  - OHLCV (1m, 5m, optionally 15m)
  - ticker / last / bid / ask
  - funding
  - open interest
  - basis / mark-index spread when available

#### Real-time path ingestion
- target transport: WebSocket / streaming
- inputs:
  - trades or ticker stream
  - liquidation events if available
  - order-book imbalance if available
  - mark / index / last divergence

### 2. Feature engine
Transforms raw market data into reusable features.

Feature groups:
- trend strength
- range/reversion metrics
- volatility compression metrics
- crowding metrics
- event shock metrics
- classifier confidence / disagreement metrics

### 3. Regime classifier
Consumes features and emits:
- `primary_regime`
- `confidence`
- `secondary_candidates`
- `reasons`

Phase 1 classifier approach:
- deterministic rules first
- ML later as a replacement or overlay

### 4. Strategy routers
Maps regime -> strategy family -> execution account.

Current routing table:
- `trend` -> account `trend`
- `range` -> account `meanrev`
- `compression` -> account `compression`
- `crowded` -> account `crowded`
- `shock` -> account `realtime`
- `chaotic` -> no account / no-trade

### 5. Execution engines
Two separate execution paths:

#### Minute execution engine
- market refresh: 10s/15s
- evaluation cadence: 1m
- uses bar-based strategies
- suitable for `trend`, `range`, `compression`, `crowded`

#### Real-time execution engine
- streaming updates
- event-driven evaluation
- suitable for `shock`
- tighter anti-repeat, in-flight lock, slippage controls

### 6. State & audit
Tracks:
- current regime and confidence
- active strategy account
- open positions by account/symbol
- per-account PnL and exposure
- recent decisions and reasons
- risk-off / no-trade state transitions

---

## Frequency model
Separate these three concepts:

1. **market update frequency**
   - default target: 10s or 15s
2. **decision frequency**
   - minute path: 1m
   - realtime path: event-driven
3. **strategy timeframe**
   - trend / range / compression / crowded may still use 1m/5m structures
   - shock reacts to live event state, not only closed bars

These three must never be conflated.

---

## Regime definitions (phase 1)

### trend
Candidate signals:
- ADX above threshold
- EMA20 and EMA50 slope aligned
- price stays on one side of EMA20
- rolling highs/lows keep advancing in one direction

### range
Candidate signals:
- ADX below threshold
- medium-low band width
- price oscillates around VWAP or middle band
- repeated reversion after deviation

### compression
Candidate signals:
- Bollinger bandwidth in low percentile
- realized volatility in low percentile
- shrinking recent candle ranges
- narrowing local range structure

### crowded
Candidate signals:
- extreme funding percentile
- OI acceleration
- basis deviation stretched
- one-sided positioning plus reversal confirmation

### shock
Candidate signals:
- 1-5 minute shock expansion
- liquidation spike
- order-book imbalance spike
- fast deviation from VWAP/mark followed by reclaim

### chaotic
Candidate signals:
- low classifier confidence
- regime flips too frequently
- breakout confirmation failure rate elevated
- major indicators disagree

---

## Why `chaotic` is first-class
A large share of trading losses comes from forcing trades in structurally unclear conditions.

Therefore `chaotic` must be explicit and legal.
The system is allowed to do nothing.

---

## ML role
Preferred ML role:
- regime classification
- regime transition prediction
- confidence estimation

Not the first target:
- direct price prediction
- blind optimization of strategy parameters without regime context

Phase progression:
1. rules-only classifier
2. supervised ML regime classifier
3. hybrid rules + ML confidence arbitration

---

## Account model
Accounts are named by regime-role, not by historical aliases.

Active account set:
- `trend`
- `meanrev`
- `compression`
- `crowded`
- `realtime`

No-trade state:
- `chaotic`

---

## Execution safety requirements

### Common
- position/account isolation
- account-aware state keys
- anti-duplicate signal locks
- in-flight order lock
- cooldown / re-entry policy
- explicit flatten policy on state mismatch

### Real-time only
- event debounce
- spread/slippage guard
- stale-feed detection
- confirmation that trigger still holds after order latency

---

## Market data hub model

One data backbone, multiple consumption views:
- raw feed ingestion is unified
- trend/range/compression/crowded/shock each read their own derived view
- strategies do not all consume the same raw microstructure stream directly

Current implementation skeleton:
- `src/market/models.py`
- `src/market/views.py`
- `src/market/hub.py`

## Proposed directory model

```text
src/
  v2/
    config/
    market/
    features/
    regimes/
    routing/
    execution/
    state/
    strategies/
    runners/
```

---

## Phase 1 deliverables
1. BTC-only config
2. canonical account registry for 5 accounts
3. regime enum + routing table
4. feature snapshot schema
5. classifier interface
6. minute-engine interface
7. realtime-engine interface
8. no-trade / chaotic state support

---

## Explicit non-goals for phase 1
- full real-money deployment
- cross-asset portfolio logic
- production-grade ML classifier
- final dashboard polish
- advanced portfolio allocation between multiple simultaneous regimes

---

## Current migration note
The old crypto scaffold remains in the repo as legacy code.
New work should land under `src/` and treat old runner/strategy implementations as reference material only.

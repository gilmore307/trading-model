# Market-State Feature Inventory v1

_Last updated: 2026-03-20_

## Purpose

This file defines the first-wave data and feature inventory for market-state description.

The goal is not to collect every possible market microstructure input immediately.
The goal is to collect enough high-value data to support:
- descriptive market-state slicing
- latent-state experiments later
- conditional family/parameter performance modeling

## Priority tiers

## Tier 1 — required for v1

### 1. OHLCV

Base fields:
- timestamp
- open
- high
- low
- close
- volume
- quote volume if available
- trade count if available from candle source

Derived features:
- multi-horizon returns
- realized volatility
- ATR / range features
- rolling range compression / expansion
- moving-average distance / slope
- candle-body and wick structure
- breakout distance from rolling extrema

Why required:
- all later state work depends on basic price/volatility structure

### 2. Trades / participation flow

Target fields:
- timestamp
- price
- size
- side / aggressor side if available
- trade count or per-window trade count

Derived features:
- trade-count burst score
- volume burst score
- taker buy vs sell imbalance
- average trade size
- signed flow imbalance by rolling window

Why required:
- captures participation intensity not visible from candles alone

### 3. Open interest

Target fields:
- timestamp
- open interest level
- open interest value if available

Derived features:
- OI change
- OI change z-score
- OI trend slope
- OI-price divergence measures

Why required:
- helps identify leverage build-up, crowding, and squeeze risk

### 4. Funding rate

Target fields:
- timestamp
- funding rate

Derived features:
- funding level
- funding change
- rolling funding percentile
- funding persistence / sign streak

Why required:
- important for crowding and directional positioning context

### 5. Basis / premium

Target fields:
- timestamp
- basis / premium value

Derived features:
- basis level
- basis slope
- normalized basis percentile
- basis divergence vs price direction

Why required:
- helps distinguish healthy trend from stressed or crowded futures-led pricing

## Tier 2 — strongly recommended next

### 6. Liquidation / forced-position data

Target fields:
- timestamp
- liquidation side
- liquidation size / notional

Derived features:
- long-liq burst
- short-liq burst
- liquidation imbalance
- liquidation shock score

Why useful:
- strong signal for panic, squeeze, and unstable transition states

### 7. Multi-timescale aggregation

Not a new raw source, but a required derived layer.

Target derived windows:
- 1m
- 5m
- 15m
- 1h

Why useful:
- state recognition usually needs both local and broader context

### 8. Derived volatility/compression layer

Examples:
- realized volatility ratio across windows
- bandwidth / squeeze features
- rolling compression duration
- expansion-after-compression markers

Why useful:
- many family choices depend on whether the market is compressing, expanding, or already extended

## Tier 3 — later enhancement

### 9. Order book imbalance

Potential fields:
- top-of-book bid/ask
- depth imbalance
- spread
- short-window book pressure measures

Why later:
- high potential value, but higher complexity and lower first-wave necessity than OHLCV + trades + OI + funding + basis

### 10. Richer microstructure channels

Examples:
- queue dynamics
- cancellation pressure
- deeper book event rates
- short-horizon execution friction proxies

Why later:
- useful for high-frequency refinement, but not first-wave critical for family-level historical research

## First-wave feature groups

## Group A — price structure

Examples:
- return_1m / 5m / 15m / 1h
- rolling volatility
- ATR-normalized move size
- trend slope
- distance from rolling highs/lows
- MA spread / MA slope family features
- compression vs expansion score

## Group B — participation / flow

Examples:
- trade-count z-score
- volume z-score
- aggressor imbalance
- burst intensity
- flow persistence

## Group C — derivatives crowding
n
Examples:
- OI level and acceleration
- funding level and slope
- basis level and slope
- price up + OI up combinations
- price up + funding up + basis up combinations

## Group D — cross-timescale context

Examples:
- 1m vs 15m trend alignment
- short-vol vs long-vol ratio
- short-horizon expansion inside long-horizon compression
- intraday extension vs higher-timeframe drift

## Feature quality rules

Each candidate feature should be reviewed for:
- availability over long history
- timestamp alignment practicality
- leakage risk
- stability across download gaps
- explanatory usefulness in downstream family/parameter separation

Do not keep features only because they sound sophisticated.
Keep them if they improve state separation or downstream utility estimation.

## Immediate implementation rule

The first implementation target should use:
- OHLCV
- trades / trade-count participation features
- OI
- funding
- basis
- multi-timescale derived features

That is enough to build a strong first version of the market-state layer.

Order book imbalance and deeper microstructure should be treated as v2 enhancement rather than a blocker for v1.

## Data-acquisition implication

Current project priority should therefore be:
1. finish long-span candle acquisition
2. improve reliable trades history acquisition
3. improve reliable OI / funding / basis history acquisition
4. normalize all of the above into a single feature-ready storage layout
5. only then start the first formal market-state dataset build

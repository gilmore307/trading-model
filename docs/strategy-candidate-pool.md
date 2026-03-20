# Strategy Candidate Pool

_Last updated: 2026-03-20_

This file is the canonical candidate pool for historical strategy research.

Rules:
- the pool is **not capped**
- candidates are tested by **family batches**
- the goal is not to keep all candidates, but to select the best family champions
- each family should evolve toward **dynamic parameters**

## Status labels

Use these labels as the pool grows:
- `idea`
- `specified`
- `implemented`
- `backtested`
- `reviewed`
- `promoted`
- `rejected`

## Current first-wave family pool

### 1. Moving Average family
Goal: not just best fixed windows, but best dynamic MA logic.

Candidates:
- MA crossover baseline variants (e.g. 5/20, 10/30, 20/60, 30/90, 50/200)
- MA family with volatility-adaptive windows
- MA family with trend-strength-adaptive windows
- MA family with time/session-sensitive windows

Status: `idea`

### 2. Donchian / breakout family
Candidates:
- Donchian 20-bar breakout
- Donchian 50-bar breakout
- breakout with volatility filter
- breakout with adaptive window length

Status: `idea`

### 3. MACD family
Candidates:
- standard MACD trend version
- faster MACD version
- MACD with trend filter
- MACD with volatility filter
- MACD with dynamic fast/slow lengths

Status: `idea`

### 4. Bollinger mean-reversion family
Candidates:
- Bollinger 20 / 2 sigma
- Bollinger 20 / 2.5 sigma
- Bollinger with trend filter
- Bollinger with volatility-conditioned width

Status: `idea`

### 5. RSI reversal family
Candidates:
- RSI14 30/70
- RSI7 20/80
- RSI with higher-timeframe trend filter
- RSI with dynamic thresholds

Status: `idea`

### 6. Bias / deviation-reversion family
Candidates:
- MA20 deviation reversion
- MA50 deviation reversion
- adaptive bias thresholds
- bias with volatility filter

Status: `idea`

### 7. Range / opening breakout family
Candidates:
- 30-bar range breakout
- 60-bar range breakout
- opening 15m breakout
- opening 30m breakout
- filtered versions with volume/volatility confirmation

Status: `idea`

### 8. Volatility-breakout family
Candidates:
- ATR breakout baseline
- realized-volatility breakout baseline
- volatility breakout with directional filter
- dynamic threshold volatility breakout

Status: `idea`

### 9. Grid family
Candidates:
- fixed grid spacing
- volatility-scaled grid spacing
- trend-aware grid disable rules
- dynamic grid compression/expansion

Status: `idea`

### 10. Multi-factor scoring family
Candidates:
- trend + momentum + volatility score
- score-based entry filter over simpler baseline families
- dynamic factor weighting

Status: `idea`

## Deferred for now

These are explicitly not first-wave priorities in the current single-market historical buildout:
- cross-exchange arbitrage
- spot/futures basis arbitrage
- funding-rate arbitrage

## Strategic future targets

Keep these as long-term targets, not immediate first-wave deliverables:
- classification-prediction strategies
- reinforcement-learning-enhanced strategies

## Selection rule

A family/candidate can be rejected if:
- it is fully covered/dominated by another candidate
- it shows no special advantage in any useful time segment
- it adds complexity without enough edge
- it cannot survive realistic drawdown/control requirements

## Milestone rule

A first useful milestone is reached after roughly **20 serious candidate variants** have been tested and reviewed.
That does not cap the pool; it only marks the point where the framework should become useful enough to support both historical and live work more confidently.

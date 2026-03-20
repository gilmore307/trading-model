# Strategy Family Implementation Plan

_Last updated: 2026-03-20_

## Current implementation direction

The first concrete family implementation step is the **moving average family**.

This first step is intentionally modest:
- not a full historical backtest engine yet
- not yet dynamic-parameter optimization
- but enough to create a family registry, baseline variants, and a batchable family runner

## First implemented family

### Moving Average family

Current baseline variants:
- MA 5 / 20
- MA 8 / 24
- MA 10 / 30
- MA 20 / 60
- MA 30 / 90
- MA 50 / 200

Dynamic-parameter targets:
- volatility-adaptive windows
- trend-strength-adaptive windows
- session-sensitive windows

## Current code pieces

- `src/research/family_registry.py`
- `src/research/ma_family.py`
- `scripts/research/run_ma_family_baselines.py`

## What the current MA family runner does

Given normalized 1-minute candle JSONL:
- compute MA baselines for each configured pair
- count crossover actions
- measure simple average MA spread
- output a family baseline summary JSON artifact

## What it does not do yet

- full pnl backtest
- slippage/fees
- dynamic-parameter switching
- family champion selection
- cross-family comparison

## Why this step still matters

It establishes the family-based execution pattern:
- family registry
- baseline variant list
- one family runner script
- one family report artifact

This is the right shape for later family-by-family expansion.

## Next implementation steps

1. add more family runners after MA family
2. turn MA family from baseline summaries into full historical backtests
3. add dynamic-parameter variants for MA family
4. define cross-family comparable review outputs

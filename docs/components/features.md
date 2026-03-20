# v2 feature engine

The phase-1 feature engine converts unified hub snapshots into classifier inputs.

Initial feature families:
- trend strength (ADX-like, EMA slopes)
- volatility structure (bandwidth, realized vol)
- reversion context (VWAP deviation z-score)
- derivatives context (basis, funding placeholders)
- event context (liquidation spike, order-book imbalance)

This layer intentionally starts simple and deterministic.

# v2 market data hub

The v2 market layer uses **one shared market data hub**.

## Principle
- One ingestion backbone
- Multiple derived views
- Each strategy consumes only the abstraction level it needs

## Raw inputs expected
- bars: 1m / 5m / 15m / 1h / 4h
- ticker / mark / index
- best bid/ask
- derivatives structure: funding / OI / basis
- derivatives history window for percentile / acceleration features
- recent trades
- liquidation events

## Strategy views
- `trend_view(symbol)`
- `meanrev_view(symbol)`
- `compression_view(symbol)`
- `crowded_view(symbol)`
- `realtime_view(symbol)`

## Realtime event ingestion
The hub also supports normalized event batches for shock/realtime work:
- top-of-book updates
- recent trades
- liquidation events

Current v1 implementation pieces:
- `src/market/streaming.py` for normalization
- `src/market/okx_ws.py` for minimal OKX public websocket ingestion
- `src/runners/shock_monitor.py` for a runnable shock observer

## Why
This keeps ingestion unified without forcing all strategies to make decisions on the same raw microstructure feed.

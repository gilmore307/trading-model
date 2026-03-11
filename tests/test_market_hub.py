from datetime import UTC, datetime

from src.market.hub import MarketDataHub
from src.market.models import Bar, DerivativesSnapshot, LiquidationEvent, OrderBookTop, TickerSnapshot, TradePrint


def test_market_hub_builds_strategy_specific_views():
    ts = datetime.now(UTC)
    hub = MarketDataHub()
    symbol = 'BTC-USDT-SWAP'

    hub.ingest_bar(symbol, '1m', Bar(ts=ts, open=1, high=2, low=0.5, close=1.5, volume=10))
    hub.ingest_bar(symbol, '5m', Bar(ts=ts, open=1, high=2, low=0.5, close=1.5, volume=10))
    hub.ingest_bar(symbol, '15m', Bar(ts=ts, open=1, high=2, low=0.5, close=1.5, volume=10))
    hub.ingest_bar(symbol, '1h', Bar(ts=ts, open=1, high=2, low=0.5, close=1.5, volume=10))
    hub.ingest_bar(symbol, '4h', Bar(ts=ts, open=1, high=2, low=0.5, close=1.5, volume=10))
    hub.ingest_ticker(symbol, TickerSnapshot(ts=ts, last=1.5, bid=1.4, ask=1.6, mark=1.5, index=1.45))
    hub.ingest_top(symbol, OrderBookTop(ts=ts, bid_price=1.4, bid_size=100, ask_price=1.6, ask_size=120))
    hub.ingest_derivatives(symbol, DerivativesSnapshot(ts=ts, funding_rate=0.01, open_interest=123, basis_pct=0.02))
    hub.ingest_trade(symbol, TradePrint(ts=ts, price=1.5, size=2.0, side='buy'))
    hub.ingest_liquidation(symbol, LiquidationEvent(ts=ts, side='sell', price=1.45, size=10, notional=14.5))

    trend_view = hub.trend_view(symbol)
    meanrev_view = hub.meanrev_view(symbol)
    compression_view = hub.compression_view(symbol)
    crowded_view = hub.crowded_view(symbol)
    realtime_view = hub.realtime_view(symbol)

    assert len(trend_view.bars_4h) == 1
    assert len(meanrev_view.bars_15m) == 1
    assert compression_view.derivatives is not None
    assert crowded_view.derivatives is not None
    assert len(realtime_view.recent_trades) == 1
    assert len(realtime_view.recent_liquidations) == 1

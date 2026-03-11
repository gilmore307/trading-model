from datetime import UTC, datetime, timedelta

from src.features.engine import FeatureEngine
from src.market.hub import MarketDataHub
from src.market.models import Bar, TickerSnapshot
from src.market.streaming import ShockStreamAdapter


def _bars(count: int, step: float = 0.2, start: float = 100.0):
    ts = datetime.now(UTC) - timedelta(minutes=count)
    out = []
    price = start
    for i in range(count):
        out.append(Bar(ts=ts + timedelta(minutes=i), open=price, high=price + 1, low=price - 1, close=price + 0.5, volume=10 + i))
        price += step
    return out


def test_realtime_batch_enriches_event_features():
    hub = MarketDataHub()
    symbol = 'BTC-USDT-SWAP'
    now = datetime.now(UTC)
    for tf in ['1m', '15m', '4h']:
        for bar in _bars(80, step=1.0 if tf == '1m' else 0.3):
            hub.ingest_bar(symbol, tf, bar)
    hub.ingest_ticker(symbol, TickerSnapshot(ts=now, last=150.0, bid=149.9, ask=150.1))

    s = ShockStreamAdapter()
    top = s.normalize_top(bid_price=149.8, bid_size=50, ask_price=150.2, ask_size=200)
    trades = [s.normalize_trade(price=150.0, size=3.0, side='buy') for _ in range(5)]
    liqs = [s.normalize_liquidation(side='sell', price=149.0, size=10.0, notional=1490.0) for _ in range(4)]
    hub.ingest_realtime_batch(symbol, top=top, trades=trades, liquidations=liqs)

    snap = hub.snapshot(symbol)
    features = FeatureEngine(layer_name='event_1m').build(snap)
    assert features.orderbook_imbalance is not None
    assert features.liquidation_spike_score is not None
    assert features.meta['trade_count_window'] == 5.0
    assert features.meta['liquidation_count_window'] == 4.0

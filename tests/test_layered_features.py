from datetime import UTC, datetime, timedelta

from src.features.engine import FeatureEngine
from src.market.models import Bar, MarketSnapshot, TickerSnapshot


def _bars(count: int, step: float = 0.2, start: float = 100.0):
    ts = datetime.now(UTC) - timedelta(minutes=count)
    out = []
    price = start
    for i in range(count):
        out.append(Bar(ts=ts + timedelta(minutes=i), open=price, high=price + 1, low=price - 1, close=price + 0.5, volume=10 + i))
        price += step
    return out


def test_layered_feature_engine_marks_layer_and_timeframe():
    snap = MarketSnapshot(
        symbol='BTC-USDT-SWAP',
        updated_at=datetime.now(UTC),
        ticker=TickerSnapshot(ts=datetime.now(UTC), last=120.0),
        bars={
            '1m': _bars(80, step=1.0),
            '15m': _bars(80, step=0.4),
            '4h': _bars(80, step=0.1),
        },
    )
    bg = FeatureEngine(trend_timeframe='4h', range_timeframe='4h', event_timeframe='1m', layer_name='background_4h').build(snap)
    primary = FeatureEngine(trend_timeframe='15m', range_timeframe='15m', event_timeframe='1m', layer_name='primary_15m').build(snap)
    event = FeatureEngine(trend_timeframe='15m', range_timeframe='15m', event_timeframe='1m', layer_name='event_1m').build(snap)

    assert bg.layer == 'background_4h'
    assert bg.source_timeframe == '4h'
    assert primary.layer == 'primary_15m'
    assert primary.source_timeframe == '15m'
    assert event.layer == 'event_1m'
    assert event.source_timeframe == '1m'
    assert 'bars_event' in event.meta

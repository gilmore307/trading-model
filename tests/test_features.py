from datetime import UTC, datetime, timedelta

from src.features.engine import FeatureEngine
from src.market.models import Bar, DerivativesSnapshot, MarketSnapshot, OrderBookTop, TickerSnapshot


def _bars(count: int, start: float = 100.0, step: float = 1.0):
    ts = datetime.now(UTC) - timedelta(minutes=count)
    out = []
    price = start
    for i in range(count):
        out.append(Bar(ts=ts + timedelta(minutes=i), open=price, high=price + 1, low=price - 1, close=price + 0.5, volume=10 + i))
        price += step
    return out


def test_feature_engine_builds_core_fields():
    now = datetime.now(UTC)
    snapshot = MarketSnapshot(
        symbol='BTC-USDT-SWAP',
        updated_at=now,
        ticker=TickerSnapshot(ts=now, last=150.0, bid=149.9, ask=150.1),
        top=OrderBookTop(ts=now, bid_price=149.9, bid_size=120, ask_price=150.1, ask_size=80),
        derivatives=DerivativesSnapshot(ts=now, funding_rate=0.01, open_interest=1000000, basis_pct=0.02),
        bars={
            '1m': _bars(80, start=100, step=0.2),
            '15m': _bars(80, start=100, step=0.5),
        },
    )
    features = FeatureEngine().build(snapshot)
    assert features.symbol == 'BTC-USDT-SWAP'
    assert features.last_price == 150.0
    assert features.adx is not None
    assert features.ema20_slope is not None
    assert features.bollinger_bandwidth_pct is not None
    assert features.orderbook_imbalance is not None
    assert features.basis_deviation_pct == 0.02

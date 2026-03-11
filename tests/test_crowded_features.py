from datetime import UTC, datetime, timedelta

from src.features.engine import FeatureEngine
from src.market.models import Bar, DerivativesSnapshot, MarketSnapshot, TickerSnapshot


def _bars(count: int, step: float = 0.2, start: float = 100.0):
    ts = datetime.now(UTC) - timedelta(minutes=count)
    out = []
    price = start
    for i in range(count):
        out.append(Bar(ts=ts + timedelta(minutes=i), open=price, high=price + 1, low=price - 1, close=price + 0.5, volume=10 + i))
        price += step
    return out


def test_feature_engine_builds_crowded_inputs_from_derivatives_history():
    now = datetime.now(UTC)
    history = []
    for i in range(20):
        history.append(
            DerivativesSnapshot(
                ts=now - timedelta(minutes=20 - i),
                funding_rate=0.001 * i,
                open_interest=1000 + i * 50,
                basis_pct=0.001 * i,
            )
        )
    snapshot = MarketSnapshot(
        symbol='BTC-USDT-SWAP',
        updated_at=now,
        ticker=TickerSnapshot(ts=now, last=150.0),
        derivatives=history[-1],
        derivatives_history=history,
        bars={
            '1m': _bars(80, step=0.2),
            '15m': _bars(80, step=0.4),
        },
    )
    features = FeatureEngine(layer_name='primary_15m').build(snapshot)
    assert features.funding_pctile is not None
    assert features.oi_accel is not None
    assert features.basis_deviation_pct is not None
    assert features.meta['derivatives_history_len'] == 20.0

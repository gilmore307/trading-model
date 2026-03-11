from datetime import UTC, datetime

from src.features.models import FeatureSnapshot
from src.regimes.classifier import RuleBasedRegimeClassifier
from src.regimes.models import Regime


def test_shock_classifier_triggers_without_liquidations_when_trade_and_book_burst_present():
    snap = FeatureSnapshot(
        ts=datetime.now(UTC),
        symbol='BTC-USDT-SWAP',
        layer='event_1m',
        realized_vol_pct=0.88,
        trade_burst_score=0.9,
        liquidation_spike_score=0.0,
        orderbook_imbalance=0.82,
        vwap_deviation_z=1.9,
    )
    out = RuleBasedRegimeClassifier().classify(snap)
    assert out.primary == Regime.SHOCK

from datetime import UTC, datetime

from src.features.models import FeatureSnapshot
from src.regimes.classifier import RuleBasedRegimeClassifier
from src.regimes.models import Regime


def _base(**kwargs):
    return FeatureSnapshot(ts=datetime.now(UTC), symbol='BTC-USDT-SWAP', **kwargs)


def test_classifier_prefers_shock_override():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(realized_vol_pct=0.99, liquidation_spike_score=0.95, orderbook_imbalance=0.8, vwap_deviation_z=2.5))
    assert out.primary == Regime.SHOCK


def test_classifier_prefers_crowded_override_when_no_shock():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(funding_pctile=0.97, oi_accel=0.8, basis_deviation_pct=0.02, vwap_deviation_z=2.2, realized_vol_pct=0.4, liquidation_spike_score=0.1))
    assert out.primary == Regime.CROWDED


def test_classifier_detects_trend():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(adx=32, ema20_slope=0.8, ema50_slope=0.4, vwap_deviation_z=1.5, realized_vol_pct=0.5))
    assert out.primary == Regime.TREND


def test_classifier_detects_range():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(adx=11, vwap_deviation_z=1.0, bollinger_bandwidth_pct=0.22, realized_vol_pct=0.3))
    assert out.primary == Regime.RANGE


def test_classifier_detects_compression():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(adx=14, bollinger_bandwidth_pct=0.05, realized_vol_pct=0.05, vwap_deviation_z=0.2))
    assert out.primary == Regime.COMPRESSION


def test_classifier_falls_back_to_chaotic_when_scores_weak():
    c = RuleBasedRegimeClassifier()
    out = c.classify(_base(adx=20, bollinger_bandwidth_pct=0.18, realized_vol_pct=0.45, vwap_deviation_z=0.1))
    assert out.primary == Regime.CHAOTIC

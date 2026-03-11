from datetime import datetime, UTC

from src.features.models import FeatureSnapshot
from src.regimes.classifier import RuleBasedRegimeClassifier
from src.regimes.models import Regime
from src.runners.minute_engine import MinuteEngine


def test_minute_engine_routes_trend():
    snapshot = FeatureSnapshot(
        ts=datetime.now(UTC),
        symbol="BTC-USDT-SWAP",
        adx=30,
        ema20_slope=1.2,
        ema50_slope=0.8,
    )
    engine = MinuteEngine(RuleBasedRegimeClassifier())
    result = engine.evaluate(snapshot)
    assert result.regime_decision.primary == Regime.TREND
    assert result.route_decision.account == "trend"
    assert result.route_decision.trade_enabled is True


def test_minute_engine_routes_chaotic_when_no_rule_matches():
    snapshot = FeatureSnapshot(
        ts=datetime.now(UTC),
        symbol="BTC-USDT-SWAP",
    )
    engine = MinuteEngine(RuleBasedRegimeClassifier())
    result = engine.evaluate(snapshot)
    assert result.regime_decision.primary == Regime.CHAOTIC
    assert result.route_decision.account is None
    assert result.route_decision.trade_enabled is False

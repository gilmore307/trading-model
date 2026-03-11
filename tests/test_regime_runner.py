from datetime import UTC, datetime

from src.features.models import FeatureSnapshot
from src.regimes.models import Regime, RegimeDecision
from src.runners.regime_runner import BtcRegimeRunner


class DummyIngestor:
    def poll(self):
        return None


class DummyLayered:
    def classify(self, snapshot):
        trend = RegimeDecision(primary=Regime.TREND, confidence=0.8, reasons=['test'], secondary=[])
        feat = FeatureSnapshot(ts=datetime.now(UTC), symbol='BTC-USDT-SWAP', layer='test', source_timeframe='15m')
        return type('LayeredOut', (), {
            'background_4h': trend,
            'primary_15m': trend,
            'override_1m': None,
            'final': trend,
            'background_features': feat,
            'primary_features': feat,
            'override_features': feat,
        })()


def test_regime_runner_outputs_trend_route():
    runner = BtcRegimeRunner.__new__(BtcRegimeRunner)
    runner.symbol = 'BTC-USDT-SWAP'
    runner.hub = type('Hub', (), {'snapshot': lambda self, symbol: object()})()
    runner.ingestor = DummyIngestor()
    runner.ws = type('WS', (), {})()
    runner.layered = DummyLayered()

    payload = runner.run_once()
    assert payload.final_decision['primary'] == Regime.TREND.value
    assert payload.route_decision['account'] == 'trend'

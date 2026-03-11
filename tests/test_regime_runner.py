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


class DummyLayeredLowConfidence:
    def classify(self, snapshot):
        chaotic = RegimeDecision(primary=Regime.CHAOTIC, confidence=0.2, reasons=['weak_signal'], secondary=[Regime.RANGE])
        feat = FeatureSnapshot(ts=datetime.now(UTC), symbol='BTC-USDT-SWAP', layer='test', source_timeframe='15m')
        return type('LayeredOut', (), {
            'background_4h': chaotic,
            'primary_15m': chaotic,
            'override_1m': None,
            'final': chaotic,
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
    assert payload.decision_summary['trade_enabled'] is True
    assert payload.decision_summary['allow_reason'] == 'route_to_trend'
    assert 'high_confidence' in payload.decision_summary['diagnostics']


def test_regime_runner_outputs_blocked_summary_for_non_tradable_regime():
    runner = BtcRegimeRunner.__new__(BtcRegimeRunner)
    runner.symbol = 'BTC-USDT-SWAP'
    runner.hub = type('Hub', (), {'snapshot': lambda self, symbol: object()})()
    runner.ingestor = DummyIngestor()
    runner.ws = type('WS', (), {})()
    runner.layered = DummyLayeredLowConfidence()

    payload = runner.run_once()
    assert payload.final_decision['primary'] == Regime.CHAOTIC.value
    assert payload.route_decision['account'] is None
    assert payload.decision_summary['trade_enabled'] is False
    assert payload.decision_summary['block_reason'] == 'regime_non_tradable'
    assert 'no_strategy_account_routed' in payload.decision_summary['diagnostics']

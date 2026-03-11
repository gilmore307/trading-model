from src.regimes.models import Regime, RegimeDecision
from src.routing.router import route_regime, summarize_decision


def test_route_regime_maps_range_to_meanrev():
    route = route_regime(Regime.RANGE)
    assert route.account == 'meanrev'
    assert route.trade_enabled is True
    assert route.allow_reason == 'route_to_meanrev'


def test_summarize_decision_blocks_non_tradable_regime():
    decision = RegimeDecision(primary=Regime.CHAOTIC, confidence=0.22, reasons=['weak_signal'], secondary=[Regime.RANGE])
    summary = summarize_decision(decision, route_regime(Regime.CHAOTIC))
    assert summary.trade_enabled is False
    assert summary.block_reason == 'regime_non_tradable'
    assert 'regime_marked_non_tradable' in summary.diagnostics
    assert 'no_strategy_account_routed' in summary.diagnostics


def test_summarize_decision_blocks_too_low_confidence_even_if_routed():
    decision = RegimeDecision(primary=Regime.TREND, confidence=0.2, reasons=['thin_confirmation'], secondary=[Regime.RANGE])
    summary = summarize_decision(decision, route_regime(Regime.TREND))
    assert summary.account == 'trend'
    assert summary.trade_enabled is False
    assert summary.block_reason == 'confidence_too_low'
    assert 'confidence_gate_blocked' in summary.diagnostics

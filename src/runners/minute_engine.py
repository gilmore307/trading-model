from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.features.models import FeatureSnapshot
from src.regimes.classifier import RegimeClassifier
from src.regimes.models import RegimeDecision
from src.routing.router import RouteDecision, route_regime


@dataclass(slots=True)
class MinuteEngineResult:
    observed_at: datetime
    feature_snapshot: FeatureSnapshot
    regime_decision: RegimeDecision
    route_decision: RouteDecision


class MinuteEngine:
    def __init__(self, classifier: RegimeClassifier):
        self.classifier = classifier

    def evaluate(self, snapshot: FeatureSnapshot) -> MinuteEngineResult:
        regime = self.classifier.classify(snapshot)
        route = route_regime(regime.primary)
        return MinuteEngineResult(
            observed_at=snapshot.ts,
            feature_snapshot=snapshot,
            regime_decision=regime,
            route_decision=route,
        )

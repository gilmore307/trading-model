from __future__ import annotations

from dataclasses import dataclass

from src.regimes.models import Regime


REGIME_ACCOUNT_MAP: dict[Regime, str | None] = {
    Regime.TREND: "trend",
    Regime.RANGE: "meanrev",
    Regime.COMPRESSION: "compression",
    Regime.CROWDED: "crowded",
    Regime.SHOCK: "realtime",
    Regime.CHAOTIC: None,
}


@dataclass(slots=True)
class RouteDecision:
    regime: Regime
    account: str | None
    strategy_family: str | None
    trade_enabled: bool


def route_regime(regime: Regime) -> RouteDecision:
    account = REGIME_ACCOUNT_MAP[regime]
    return RouteDecision(
        regime=regime,
        account=account,
        strategy_family=None if account is None else regime.value,
        trade_enabled=account is not None,
    )

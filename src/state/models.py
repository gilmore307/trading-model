from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.regimes.models import Regime, RegimeDecision


@dataclass(slots=True)
class AccountState:
    alias: str
    enabled: bool = True
    position_side: str | None = None
    position_size: float = 0.0
    last_signal_at: datetime | None = None
    last_decision_reason: str | None = None


@dataclass(slots=True)
class SystemState:
    symbol: str
    active_regime: Regime = Regime.CHAOTIC
    last_regime_decision: RegimeDecision | None = None
    accounts: dict[str, AccountState] = field(default_factory=dict)

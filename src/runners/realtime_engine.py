from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RealtimeTrigger:
    observed_at: datetime
    symbol: str
    trigger_type: str
    confidence: float
    reason: str


class RealtimeEngine:
    """Placeholder for event-driven strategy execution.

    Phase 1 scope is interface only. Concrete logic will consume streaming
    market updates and emit RealtimeTrigger objects.
    """

    def on_event(self, *, symbol: str, trigger_type: str, confidence: float, reason: str) -> RealtimeTrigger:
        return RealtimeTrigger(
            observed_at=datetime.utcnow(),
            symbol=symbol,
            trigger_type=trigger_type,
            confidence=confidence,
            reason=reason,
        )

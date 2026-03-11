from __future__ import annotations

from dataclasses import dataclass

from src.reconcile.alignment import ExchangePositionSnapshot
from src.state.live_position import LivePosition, LivePositionStatus


@dataclass(slots=True)
class VerificationDecision:
    next_status: LivePositionStatus
    accepted: bool
    reason: str


def verify_entry(local: LivePosition, exchange: ExchangePositionSnapshot | None) -> VerificationDecision:
    if exchange is None or exchange.side is None or float(exchange.size or 0.0) <= 0.0:
        return VerificationDecision(
            next_status=LivePositionStatus.ENTRY_VERIFYING,
            accepted=False,
            reason='missing_exchange_position_evidence',
        )
    if local.side is not None and exchange.side != local.side:
        return VerificationDecision(
            next_status=LivePositionStatus.RECONCILE_MISMATCH,
            accepted=False,
            reason='exchange_side_mismatch_during_entry_verification',
        )
    return VerificationDecision(
        next_status=LivePositionStatus.OPEN,
        accepted=True,
        reason='exchange_position_confirmed',
    )


def verify_exit(local: LivePosition, exchange: ExchangePositionSnapshot | None) -> VerificationDecision:
    if exchange is None or float(exchange.size or 0.0) <= 0.0:
        return VerificationDecision(
            next_status=LivePositionStatus.FLAT,
            accepted=True,
            reason='exchange_flat_confirmed',
        )
    return VerificationDecision(
        next_status=LivePositionStatus.EXIT_VERIFYING,
        accepted=False,
        reason='exchange_position_still_present',
    )

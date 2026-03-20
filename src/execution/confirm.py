from __future__ import annotations

from dataclasses import dataclass

from src.reconcile.alignment import ExchangePositionSnapshot
from src.state.live_position import LivePosition, LivePositionStatus


def _entry_hint(local: LivePosition) -> dict:
    meta = dict(local.meta or {})
    hint = meta.get('last_verification_hint')
    return hint if isinstance(hint, dict) else {}


def _hint_trade_confirmed(local: LivePosition) -> bool:
    hint = _entry_hint(local)
    if bool(hint.get('verified_entry')):
        return True
    attempts = hint.get('verification_attempts') or []
    return any(bool(row.get('trade_confirmed')) for row in attempts if isinstance(row, dict))


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

    target_size = float(local.ledger_open_size or local.size or 0.0)
    exchange_size = float(exchange.size or 0.0)
    size_close = abs(exchange_size - target_size) <= max(1e-9, abs(target_size) * 0.05)
    trade_confirmed = _hint_trade_confirmed(local)

    if trade_confirmed and size_close:
        return VerificationDecision(
            next_status=LivePositionStatus.OPEN,
            accepted=True,
            reason='exchange_position_trade_confirmed',
        )
    if size_close:
        return VerificationDecision(
            next_status=LivePositionStatus.OPEN,
            accepted=True,
            reason='exchange_position_confirmed',
        )
    return VerificationDecision(
        next_status=LivePositionStatus.ENTRY_VERIFYING,
        accepted=False,
        reason='exchange_position_size_unconfirmed',
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

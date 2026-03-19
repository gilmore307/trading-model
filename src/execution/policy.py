from __future__ import annotations

from dataclasses import dataclass

from src.reconcile.alignment import AlignmentIssueType, AlignmentResult


@dataclass(slots=True)
class PolicyDecision:
    trade_enabled: bool
    action: str
    reason: str


def decide_alignment_policy(result: AlignmentResult) -> PolicyDecision:
    if result.ok:
        return PolicyDecision(trade_enabled=True, action='continue', reason='alignment_ok')

    severe_types = {
        AlignmentIssueType.UNEXPECTED_EXCHANGE_POSITION,
        AlignmentIssueType.SIDE_MISMATCH,
        AlignmentIssueType.SIZE_MISMATCH,
        AlignmentIssueType.LEDGER_POSITION_MISMATCH,
    }
    if any(issue.type in severe_types for issue in result.issues):
        return PolicyDecision(trade_enabled=False, action='freeze_route', reason='severe_alignment_issue')

    return PolicyDecision(trade_enabled=False, action='verify_only', reason='alignment_requires_manual_or_delayed_confirmation')

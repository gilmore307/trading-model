from __future__ import annotations

from dataclasses import dataclass, field

from src.state.live_position import LivePosition, LivePositionStatus
from src.strategies.executors import ExecutionPlan


REGIME_PRIORITY = {
    'shock': 6,
    'crowded': 5,
    'trend': 4,
    'compression': 3,
    'range': 2,
    'chaotic': 1,
}


@dataclass(slots=True)
class SwitchContext:
    current_position: LivePosition | None
    current_strategy: str | None
    target_strategy: str | None
    target_plan: ExecutionPlan
    target_has_position: bool = False
    target_position_side: str | None = None


@dataclass(slots=True)
class SwitchDecision:
    action: str
    keep_position: bool
    adopted_strategy: str | None
    reason: str
    notes: list[str] = field(default_factory=list)


def _priority(strategy: str | None) -> int:
    if strategy is None:
        return 0
    return REGIME_PRIORITY.get(strategy, 0)


def evaluate_switch(context: SwitchContext) -> SwitchDecision:
    current = context.current_position
    target = context.target_strategy

    if current is None or current.status == LivePositionStatus.FLAT or not current.side or current.size <= 0:
        return SwitchDecision(
            action='adopt_target_plan',
            keep_position=False,
            adopted_strategy=target,
            reason='no_existing_position',
            notes=['no_existing_position'],
        )

    current_strategy = context.current_strategy or current.route

    if context.target_has_position:
        if context.target_position_side == current.side:
            return SwitchDecision(
                action='keep_current_position',
                keep_position=True,
                adopted_strategy=target,
                reason='target_same_direction_keep',
                notes=['target_has_position', 'same_direction'],
            )
        return SwitchDecision(
            action='close_and_wait',
            keep_position=False,
            adopted_strategy=target,
            reason='target_opposite_direction_close_wait',
            notes=['target_has_position', 'opposite_direction'],
        )

    current_priority = _priority(current_strategy)
    target_priority = _priority(target)

    if target_priority >= current_priority and target_priority > 0:
        return SwitchDecision(
            action='keep_current_position',
            keep_position=True,
            adopted_strategy=target,
            reason='target_priority_preserves_exposure',
            notes=[f'priority:{current_strategy or "none"}->{target}', f'{current_priority}->{target_priority}'],
        )

    return SwitchDecision(
        action='close_and_wait',
        keep_position=False,
        adopted_strategy=target,
        reason='target_priority_too_low_close_wait',
        notes=[f'priority:{current_strategy or "none"}->{target}', f'{current_priority}->{target_priority}'],
    )

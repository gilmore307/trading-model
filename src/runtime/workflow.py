from __future__ import annotations

from dataclasses import dataclass

from src.runtime.mode import RuntimeMode


@dataclass(slots=True)
class WorkflowTransition:
    from_mode: RuntimeMode
    to_mode: RuntimeMode
    reason: str


AUTO_TRANSITIONS: dict[RuntimeMode, WorkflowTransition] = {
    RuntimeMode.RESET: WorkflowTransition(from_mode=RuntimeMode.RESET, to_mode=RuntimeMode.DEVELOP, reason='reset_complete_return_to_develop'),
    RuntimeMode.TEST: WorkflowTransition(from_mode=RuntimeMode.TEST, to_mode=RuntimeMode.DEVELOP, reason='test_complete_return_to_develop'),
}


def next_mode_after(mode: RuntimeMode) -> WorkflowTransition | None:
    return AUTO_TRANSITIONS.get(mode)

from __future__ import annotations

from dataclasses import dataclass

from src.runtime.mode import RuntimeMode


@dataclass(slots=True)
class ModePolicy:
    mode: RuntimeMode
    allow_strategy_execution: bool
    force_dry_run: bool
    allow_normal_routing: bool
    requires_flatten_workflow: bool
    description: str


MODE_POLICIES: dict[RuntimeMode, ModePolicy] = {
    RuntimeMode.DEVELOP: ModePolicy(RuntimeMode.DEVELOP, allow_strategy_execution=False, force_dry_run=True, allow_normal_routing=False, requires_flatten_workflow=False, description='development mode: idle / maintenance state; strategy execution and routing blocked'),
    RuntimeMode.TEST: ModePolicy(RuntimeMode.TEST, allow_strategy_execution=False, force_dry_run=True, allow_normal_routing=False, requires_flatten_workflow=False, description='test mode: dedicated execution-system test workflow; normal strategy routing blocked'),
    RuntimeMode.TRADE: ModePolicy(RuntimeMode.TRADE, allow_strategy_execution=True, force_dry_run=False, allow_normal_routing=True, requires_flatten_workflow=False, description='trade mode: normal strategy routing and execution allowed'),
    RuntimeMode.RESET: ModePolicy(RuntimeMode.RESET, allow_strategy_execution=False, force_dry_run=True, allow_normal_routing=False, requires_flatten_workflow=True, description='reset mode: destructive development reset workflow, then return to develop'),
}


def policy_for_mode(mode: RuntimeMode) -> ModePolicy:
    return MODE_POLICIES[mode]

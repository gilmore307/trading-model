from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from src.runners.regime_runner import RegimeRunnerOutput
from src.state.live_position import LivePosition, LivePositionStatus
from src.state.store import LiveStateStore
from src.strategies.executors import ExecutionPlan, executor_for
from src.routing.switch_policy import SwitchContext, evaluate_switch


COMPOSITE_ACCOUNT = 'router_composite'


@dataclass(slots=True)
class CompositeDecision:
    account: str
    symbol: str
    selected_strategy: str | None
    source_regime: str
    source_confidence: float
    plan: ExecutionPlan
    switch_action: str
    notes: list[str] = field(default_factory=list)


class RouterCompositeSimulator:
    """Pure-simulated router-driven composite account.

    This does not use exchange APIs. It consumes the current regime/router output,
    chooses the strategy implied by the router, and keeps a lightweight virtual
    position state for review-time comparison against always-on single-strategy accounts.
    """

    def __init__(self, live_store: LiveStateStore | None = None):
        self._positions: dict[str, LivePosition] = {}
        self.live_store = live_store or LiveStateStore()

    def current_position(self, symbol: str) -> LivePosition | None:
        return self._positions.get(symbol)

    def target_strategy_position(self, strategy: str | None, symbol: str) -> LivePosition | None:
        if not strategy:
            return None
        return self.live_store.get(strategy, symbol)

    def _target_plan(self, output: RegimeRunnerOutput, selected_strategy: str) -> ExecutionPlan:
        routed_output = RegimeRunnerOutput(
            observed_at=output.observed_at,
            symbol=output.symbol,
            background_4h=output.background_4h,
            primary_15m=output.primary_15m,
            override_1m=output.override_1m,
            background_features=output.background_features,
            primary_features=output.primary_features,
            override_features=output.override_features,
            final_decision={**output.final_decision, 'primary': selected_strategy},
            route_decision={
                'regime': output.route_decision.get('regime'),
                'account': COMPOSITE_ACCOUNT,
                'strategy_family': selected_strategy,
                'trade_enabled': True,
                'allow_reason': f'composite_follow_{selected_strategy}',
                'block_reason': None,
            },
            decision_summary={
                **output.decision_summary,
                'account': COMPOSITE_ACCOUNT,
                'strategy_family': selected_strategy,
                'trade_enabled': True,
                'allow_reason': f'composite_follow_{selected_strategy}',
                'block_reason': None,
            },
        )
        plan = executor_for(routed_output).build_plan(routed_output)
        plan.account = COMPOSITE_ACCOUNT
        return plan

    def build_decision(self, output: RegimeRunnerOutput) -> CompositeDecision:
        selected_strategy = output.route_decision.get('account')
        current = self.current_position(output.symbol)
        if not selected_strategy or not output.decision_summary.get('trade_enabled', False):
            plan = ExecutionPlan(
                regime=output.final_decision['primary'],
                account=COMPOSITE_ACCOUNT,
                action='hold',
                reason=output.decision_summary.get('block_reason') or 'composite_router_hold',
            )
            notes = ['router_not_actionable']
            return CompositeDecision(
                account=COMPOSITE_ACCOUNT,
                symbol=output.symbol,
                selected_strategy=None,
                source_regime=output.final_decision['primary'],
                source_confidence=float(output.final_decision.get('confidence') or 0.0),
                plan=plan,
                switch_action='hold',
                notes=notes,
            )

        target_plan = self._target_plan(output, selected_strategy)
        target_position = self.target_strategy_position(selected_strategy, output.symbol)
        target_has_position = bool(
            target_position is not None
            and target_position.status != LivePositionStatus.FLAT
            and target_position.side is not None
            and target_position.size > 0
        )
        switch = evaluate_switch(
            SwitchContext(
                current_position=current,
                current_strategy=None if current is None else current.route,
                target_strategy=selected_strategy,
                target_plan=target_plan,
                target_has_position=target_has_position,
                target_position_side=None if target_position is None else target_position.side,
            )
        )

        if switch.action == 'keep_current_position' and current is not None:
            plan = ExecutionPlan(
                regime=selected_strategy,
                account=COMPOSITE_ACCOUNT,
                action='hold',
                side=current.side,
                size=current.size,
                reason=switch.reason,
            )
        elif switch.action == 'close_and_wait':
            plan = ExecutionPlan(
                regime=selected_strategy,
                account=COMPOSITE_ACCOUNT,
                action='exit' if current is not None and current.status != LivePositionStatus.FLAT else 'hold',
                reason=switch.reason,
            )
        else:
            plan = target_plan

        notes = [f'selected_strategy:{selected_strategy}', *switch.notes]
        if target_position is not None:
            notes.append(f'target_position_side:{target_position.side}')
            notes.append(f'target_position_size:{target_position.size}')
        return CompositeDecision(
            account=COMPOSITE_ACCOUNT,
            symbol=output.symbol,
            selected_strategy=selected_strategy,
            source_regime=output.final_decision['primary'],
            source_confidence=float(output.final_decision.get('confidence') or 0.0),
            plan=plan,
            switch_action=switch.action,
            notes=notes,
        )

    def apply(self, decision: CompositeDecision) -> LivePosition | None:
        current = self._positions.get(decision.symbol)
        plan = decision.plan
        if plan.action == 'enter' and plan.side is not None and plan.size is not None:
            opened_by = decision.selected_strategy or decision.source_regime
            current = LivePosition(
                account=COMPOSITE_ACCOUNT,
                symbol=decision.symbol,
                route=opened_by,
                status=LivePositionStatus.OPEN,
                side=plan.side,
                size=plan.size,
                reason=plan.reason,
                meta={
                    'selected_strategy': decision.selected_strategy or '',
                    'opened_by_strategy': opened_by,
                    'position_owner': opened_by,
                    'mode': 'simulated',
                    'switch_action': decision.switch_action,
                },
            )
            current.last_local_updated_at = datetime.now(UTC)
            self._positions[decision.symbol] = current
            return current
        if plan.action == 'exit':
            if current is None:
                return None
            current.status = LivePositionStatus.FLAT
            current.side = None
            current.size = 0.0
            current.reason = plan.reason
            current.meta['switch_action'] = decision.switch_action
            current.last_local_updated_at = datetime.now(UTC)
            self._positions[decision.symbol] = current
            return current
        if current is not None:
            current.reason = plan.reason
            current.meta['switch_action'] = decision.switch_action
            current.meta.setdefault('opened_by_strategy', current.route)
            current.meta.setdefault('position_owner', current.route)
            current.last_local_updated_at = datetime.now(UTC)
            self._positions[decision.symbol] = current
        return current

    def snapshot(self, output: RegimeRunnerOutput) -> dict:
        decision = self.build_decision(output)
        position = self.apply(decision)
        return {
            'account': COMPOSITE_ACCOUNT,
            'symbol': output.symbol,
            'selected_strategy': decision.selected_strategy,
            'source_regime': decision.source_regime,
            'source_confidence': decision.source_confidence,
            'switch_action': decision.switch_action,
            'position_owner': None if position is None else position.meta.get('position_owner', position.route),
            'plan': asdict(decision.plan),
            'notes': list(decision.notes),
            'position': None if position is None else asdict(position),
        }

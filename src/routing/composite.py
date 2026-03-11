from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from src.runners.regime_runner import RegimeRunnerOutput
from src.state.live_position import LivePosition, LivePositionStatus
from src.strategies.executors import ExecutionPlan, executor_for


COMPOSITE_ACCOUNT = 'router_composite'


@dataclass(slots=True)
class CompositeDecision:
    account: str
    symbol: str
    selected_strategy: str | None
    source_regime: str
    source_confidence: float
    plan: ExecutionPlan
    notes: list[str] = field(default_factory=list)


class RouterCompositeSimulator:
    """Pure-simulated router-driven composite account.

    This does not use exchange APIs. It consumes the current regime/router output,
    chooses the strategy implied by the router, and keeps a lightweight virtual
    position state for review-time comparison against always-on single-strategy accounts.
    """

    def __init__(self):
        self._positions: dict[str, LivePosition] = {}

    def current_position(self, symbol: str) -> LivePosition | None:
        return self._positions.get(symbol)

    def build_decision(self, output: RegimeRunnerOutput) -> CompositeDecision:
        selected_strategy = output.route_decision.get('account')
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
                notes=notes,
            )

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
        notes = [f'selected_strategy:{selected_strategy}']
        return CompositeDecision(
            account=COMPOSITE_ACCOUNT,
            symbol=output.symbol,
            selected_strategy=selected_strategy,
            source_regime=output.final_decision['primary'],
            source_confidence=float(output.final_decision.get('confidence') or 0.0),
            plan=plan,
            notes=notes,
        )

    def apply(self, decision: CompositeDecision) -> LivePosition | None:
        current = self._positions.get(decision.symbol)
        plan = decision.plan
        if plan.action == 'enter' and plan.side is not None and plan.size is not None:
            current = LivePosition(
                account=COMPOSITE_ACCOUNT,
                symbol=decision.symbol,
                route=decision.selected_strategy or decision.source_regime,
                status=LivePositionStatus.OPEN,
                side=plan.side,
                size=plan.size,
                reason=plan.reason,
                meta={'selected_strategy': decision.selected_strategy or '', 'mode': 'simulated'},
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
            current.last_local_updated_at = datetime.now(UTC)
            self._positions[decision.symbol] = current
            return current
        if current is not None:
            current.reason = plan.reason
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
            'plan': asdict(decision.plan),
            'notes': list(decision.notes),
            'position': None if position is None else asdict(position),
        }

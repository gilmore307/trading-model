from __future__ import annotations

from datetime import datetime
from typing import Any

from src.config.settings import Settings
from src.runners.regime_runner import RegimeRunnerOutput
from src.strategies.executors import CompressionExecutor, CrowdedExecutor, ExecutionPlan, RangeExecutor, ShockExecutor, TrendExecutor


def output_from_research_row(row: dict[str, Any], *, settings: Settings | None = None) -> RegimeRunnerOutput:
    observed_at = datetime.fromisoformat(str(row.get('timestamp') or '1970-01-01T00:00:00+00:00').replace('Z', '+00:00'))
    return RegimeRunnerOutput(
        observed_at=observed_at,
        symbol=row.get('symbol') or 'BTC-USDT-SWAP',
        background_4h={'primary': row.get('bg_regime'), 'confidence': row.get('bg_confidence')},
        primary_15m={'primary': row.get('primary_regime'), 'confidence': row.get('primary_confidence')},
        override_1m=None if row.get('override_regime') is None else {'primary': row.get('override_regime'), 'confidence': row.get('override_confidence')},
        background_features=row.get('background_features') or {},
        primary_features=row.get('primary_features') or {},
        override_features=row.get('override_features') or {},
        final_decision={'primary': row.get('final_regime'), 'confidence': row.get('final_confidence')},
        route_decision={'account': row.get('route_account') or row.get('executor_regime') or row.get('final_regime'), 'strategy_family': row.get('route_strategy_family') or row.get('final_regime'), 'trade_enabled': row.get('route_trade_enabled', True)},
        decision_summary=row.get('decision_summary') or {},
        settings=settings,
    )


def settings_with_overrides(overrides: dict[str, Any], *, base: Settings | None = None) -> Settings:
    base = base or Settings.load()
    field_names = set(getattr(base.__class__, 'model_fields', {}).keys())
    filtered = {k: v for k, v in overrides.items() if k in field_names}
    if not filtered:
        return base
    if hasattr(base, 'model_copy'):
        return base.model_copy(update=filtered)
    payload = base.model_dump() if hasattr(base, 'model_dump') else dict(base.__dict__)
    payload.update(filtered)
    return Settings(**payload)


def reevaluate_strategy_row(*, row: dict[str, Any], strategy: str, parameter_overrides: dict[str, Any] | None = None, base_settings: Settings | None = None) -> ExecutionPlan:
    shadow_plan = (row.get('shadow_plans') or {}).get(strategy)
    if shadow_plan is not None and 'timestamp' not in row and 'symbol' not in row:
        return ExecutionPlan(
            regime=row.get('final_regime') or strategy,
            account=row.get('route_account') or strategy,
            action=str(shadow_plan.get('action') or 'watch'),
            side=shadow_plan.get('side'),
            size=shadow_plan.get('size'),
            reason='shadow_plan_fallback',
            score=None if shadow_plan.get('score') is None else float(shadow_plan.get('score')),
            blockers=list(shadow_plan.get('blockers') or []),
            signals=dict(shadow_plan.get('signals') or {}),
            subscores=dict(shadow_plan.get('subscores') or {}),
        )

    settings = settings_with_overrides(parameter_overrides or {}, base=base_settings)
    output = output_from_research_row(row, settings=settings)
    if strategy == 'trend':
        return TrendExecutor().build_plan(output)
    if strategy == 'range':
        return RangeExecutor().build_plan(output)
    if strategy == 'compression':
        return CompressionExecutor().build_plan(output)
    if strategy == 'crowded':
        return CrowdedExecutor().build_plan(output)
    if strategy == 'shock':
        return ShockExecutor().build_plan(output)
    raise NotImplementedError(f'reevaluation hook not yet implemented for strategy={strategy}')
